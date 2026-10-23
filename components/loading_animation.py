"""
components/loading_animation.py
--------------------------------
Animated loading orb shown during review analysis.

Inspired by the reference image: a soft, blurred multicolour sphere
with subtle motion — implemented in pure CSS + Streamlit HTML injection.

Usage:
    placeholder = st.empty()
    loading_animation.show(placeholder, "Preparing review data...")
    # ... do work ...
    loading_animation.hide(placeholder)
"""

import json
from typing import List, Optional
import streamlit as st


_ORB_HTML = """
<div class="mezy-orb-wrapper">
  <div class="mezy-orb"></div>
  <p class="orb-status" id="orb-status-msg">{status}</p>
</div>
"""


def _build_orb_html(status: str, stages: Optional[List[str]] = None) -> str:
    """Build orb HTML with optional smooth script-based stage progression."""
    base_html = _ORB_HTML.format(status=status)
    if not stages or len(stages) <= 1:
        return base_html

    stages_json = json.dumps(stages, ensure_ascii=False)
    script_html = f"""
<script>
(function() {{
  var stages = {stages_json};
  var el = document.getElementById("orb-status-msg");
  if (!el || !stages || stages.length <= 1) return;
  var idx = 0;
  var timer = setInterval(function() {{
    idx++;
    if (idx < stages.length && el) {{
      el.textContent = stages[idx];
    }} else {{
      clearInterval(timer);
    }}
  }}, 2500);
}})();
</script>
"""
    return base_html + script_html


def show(
    placeholder: st.delta_generator.DeltaGenerator,
    status: str = "Analyzing customer reviews...",
    stages: Optional[List[str]] = None,
) -> None:
    """Render the animated orb in the given placeholder."""
    placeholder.markdown(_build_orb_html(status=status, stages=stages), unsafe_allow_html=True)


def update_status(placeholder: st.delta_generator.DeltaGenerator, status: str) -> None:
    """Replace the placeholder content with a new status message (orb stays)."""
    placeholder.markdown(_ORB_HTML.format(status=status), unsafe_allow_html=True)


def hide(placeholder: st.delta_generator.DeltaGenerator) -> None:
    """Remove the animation from the placeholder."""
    placeholder.empty()


def show_inline(
    status: str = "Analyzing customer reviews...",
    stages: Optional[List[str]] = None,
) -> None:
    """Render the orb directly into the current Streamlit position (no placeholder)."""
    st.markdown(_build_orb_html(status=status, stages=stages), unsafe_allow_html=True)

