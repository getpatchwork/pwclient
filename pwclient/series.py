import sys

def link(api, series_ids):
    try:
        api.series_linking(series_ids)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
