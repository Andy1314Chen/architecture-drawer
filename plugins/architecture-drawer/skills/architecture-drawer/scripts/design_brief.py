"""Design Brief contract — the declared design intent of a diagram (Step 1).

A DesignBrief is the machine-readable form of the Step-1 design brief: what
palette / layout / flow the author *declared* before drawing.  The contract
checker (semantic_qa.check_design_brief) then asserts the RENDERED SVG against
this declaration.

Capability boundary (deliberate): this layer verifies
**rendering <-> self-declared contract** consistency.  It does NOT verify
"contract <-> user's true intent" — the brief and the gen.py are usually
written by the same agent in the same round, so a coherently-wrong brief
passes.  Spec-entity coverage (check_text_semantics) and human review of the
brief remain the guards for intent.

Schema rules (inconsistent states are unconstructible):
  - ``palette_role`` is the SINGLE source of declared identity: its keys are
    the data-node-id values the checker looks for in the SVG.  Key semantics
    are bound to ``layout``: band -> layer-container ids, node -> primary
    node ids.  There is no separate container list to drift out of sync.
  - ``flow_chain`` is the ordered pipeline chain (a SUBSET of palette keys —
    validated at construction).  Side bands (memory/cache columns) and
    text-only bands are palette members but not chain stages; membership is
    not derivable from paint, so it is declared explicitly.
  - tint/plain membership is DERIVED from ``ColorSpec.fill`` (white == plain).
  - All colors are canonicalized through ``svg_utils.normalize_color`` to
    lowercase #rrggbb ("white" -> "#ffffff", named colors like "gray" ->
    "#808080") — the same normalizer the checker applies to rendered SVG
    fills, so hex case/alias/named tokens never produce noise failures.
"""
import json
from dataclasses import dataclass, field
from typing import Mapping, Tuple

try:
    from svg_utils import normalize_color
except ImportError:  # standalone use without the skill on sys.path
    def normalize_color(value):  # type: ignore[misc]
        return None

_WHITE = {"white", "#fff", "#ffffff"}
_LAYOUTS = ("band", "node")
_FLOWS = ("top-down", "left-right", "none")


def norm_hex(color: str) -> str:
    """Normalize a color token to lowercase #rrggbb (3-digit expanded,
    'white' family collapsed to #ffffff). Unknown tokens pass through
    lowercased so mismatches still compare deterministically."""
    c = (color or "").strip().lower()
    if c in _WHITE:
        return "#ffffff"
    if c.startswith("#") and len(c) == 4:
        return "#" + "".join(ch * 2 for ch in c[1:])
    return c


def canon_hex(color: str) -> str:
    """Canonical #rrggbb via svg_utils.normalize_color — the SAME
    normalization the checker applies to rendered fills, so a brief and the
    SVG compare on identical tokens (named colors like 'gray' resolve to hex
    on both sides). Tokens normalize_color cannot parse ('none', '',
    unknown) keep norm_hex's lowercase passthrough so is_plain still
    recognizes them."""
    c = norm_hex(color)
    return normalize_color(c) or c


def is_plain(fill: str) -> bool:
    """A plain fill reads as white/neutral canvas (not a tinted structure)."""
    return norm_hex(fill) in _WHITE or norm_hex(fill) in ("none", "")


@dataclass(frozen=True)
class ColorSpec:
    """A declared (fill, stroke) pair — the tint+accent pairing that the
    contrast check (WCAG) relies on; declaring one hex is not enough."""
    fill: str
    stroke: str

    def __post_init__(self):
        object.__setattr__(self, "fill", canon_hex(self.fill))
        object.__setattr__(self, "stroke", canon_hex(self.stroke))

    def as_pair(self) -> Tuple[str, str]:
        return (self.fill, self.stroke)

    @classmethod
    def from_json(cls, d) -> "ColorSpec":
        return cls(d["fill"], d["stroke"])


@dataclass(frozen=True)
class DesignBrief:
    scheme: str = "S1"            # preset id from references/design_specs.md
    layout: str = "band"          # band | node  (key semantics, see module doc)
    flow: str = "top-down"        # top-down | left-right | none (no dominant axis)
    # key = data-node-id (band: layer container; node: primary node)
    palette_role: Mapping[str, ColorSpec] = field(default_factory=dict)
    # ordered pipeline chain (first -> last along the flow axis): a SUBSET of
    # palette keys; side bands / text-only bands stay out of the chain.
    flow_chain: Tuple[str, ...] = ()

    def __post_init__(self):
        if self.layout not in _LAYOUTS:
            raise ValueError(
                f"layout must be one of {_LAYOUTS}, got {self.layout!r}")
        if self.flow not in _FLOWS:
            raise ValueError(
                f"flow must be one of {_FLOWS}, got {self.flow!r}")
        object.__setattr__(self, "palette_role", dict(self.palette_role))
        unknown = [k for k in self.flow_chain if k not in self.palette_role]
        if unknown:
            raise ValueError(
                f"flow_chain keys not declared in palette_role: {unknown}")

    # -- derived views (single source of truth: palette_role) ---------------
    @property
    def tint_keys(self) -> Tuple[str, ...]:
        """Declared keys whose fill carries structure color (tinted)."""
        return tuple(k for k, s in self.palette_role.items()
                     if not is_plain(s.fill))

    @property
    def plain_keys(self) -> Tuple[str, ...]:
        """Declared keys that stay white-bottomed (op cards)."""
        return tuple(k for k, s in self.palette_role.items()
                     if is_plain(s.fill))

    @property
    def layers(self) -> Tuple[str, ...]:
        """Ordered chain stages (first -> last along the flow axis): the
        declared flow_chain. Empty for node-style briefs / no chain."""
        return tuple(self.flow_chain)

    # -- serialization (brief.json next to the artifact triplet) -----------
    def to_dict(self) -> dict:
        return {
            "scheme": self.scheme,
            "layout": self.layout,
            "flow": self.flow,
            "flow_chain": list(self.flow_chain),
            "palette_role": {k: {"fill": s.fill, "stroke": s.stroke}
                             for k, s in self.palette_role.items()},
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d) -> "DesignBrief":
        return cls(
            scheme=d.get("scheme", "S1"),
            layout=d.get("layout", "band"),
            flow=d.get("flow", "top-down"),
            flow_chain=tuple(d.get("flow_chain", ())),
            palette_role={k: ColorSpec.from_json(v)
                          for k, v in d.get("palette_role", {}).items()},
        )

    @classmethod
    def from_json(cls, text: str) -> "DesignBrief":
        return cls.from_dict(json.loads(text))

    @classmethod
    def load(cls, path) -> "DesignBrief":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_json(fh.read())

    def write(self, path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())


def load_brief_file(path) -> "DesignBrief":
    """Convenience loader used by gen.py / tests; returns None when absent."""
    try:
        return DesignBrief.load(path)
    except FileNotFoundError:
        return None
