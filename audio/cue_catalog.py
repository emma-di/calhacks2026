"""Approved friendly cue groups shared by settings, recognition and display.

This is a selection catalog, not a claim of calibrated recognition accuracy. Builtin groups keep
using their existing detector/event contract; custom groups are enabled only by a saved selection.
"""
import json
from pathlib import Path

CUES = json.loads(Path(__file__).with_name('cue-catalog.json').read_text())['cues']
CUES_BY_ID = {cue['id']: cue for cue in CUES}
LABEL_CUE_ICONS = {}
for cue in CUES:
    for label in cue['model_labels']:
        LABEL_CUE_ICONS.setdefault(label, cue['icon_id'])


def selected_cue(request):
    """Resolve a saved curated rule, refusing stale/mismatched model-label mappings."""
    cue_id = request.get('cue_id')
    if cue_id is None:
        return None
    cue = CUES_BY_ID.get(cue_id) if isinstance(cue_id, str) else None
    if cue is None or cue['event_type'] != 'custom':
        raise ValueError('Custom cue_id must identify a supported custom cue')
    if request.get('model_labels') != cue['model_labels']:
        raise ValueError('Curated cue model_labels must match its approved group')
    return cue
