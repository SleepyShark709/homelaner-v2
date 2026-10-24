"""Release focused queries only after a successful REA inventory response.

An import timeout must not cause every queued query to repeat the same expensive
import. This collector gates that batch and preserves the original response.
"""
import json
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'research/rea-audit/session-focused'
overview = root / 'responses/003-overview.json'
deadline = time.monotonic() + 4000
while time.monotonic() < deadline:
    if overview.exists():
        try:
            response = json.loads(overview.read_text(encoding='utf8'))
        except json.JSONDecodeError:
            time.sleep(1)
            continue
        failed = 'error' in response or response.get('result', {}).get('isError', False)
        if not failed:
            for path in sorted((root / 'after-overview').glob('*.json')):
                path.rename(root / 'requests' / path.name)
        (root / 'collection-status.json').write_text(json.dumps({'state': 'stopped_on_overview_error' if failed else 'released_queries', 'overview': str(overview)}, indent=2), encoding='utf8')
        print('Overview failed; queries withheld.' if failed else 'Overview succeeded; focused queries released.', flush=True)
        break
    time.sleep(2)
else:
    raise TimeoutError('No complete overview response; focused queries remain withheld.')
