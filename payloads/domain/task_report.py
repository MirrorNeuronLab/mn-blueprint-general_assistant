"""Present the saved answer and content-free action evidence."""


def document(result, answer, audit):
    actions = audit['actions']
    rows = [[i, action['action'], str(action.get('outcome') or 'Unconfirmed').replace('_', ' ')]
            for i, action in enumerate(actions, 1)]
    if result['requires_reconciliation']:
        next_step = 'Inspect the target app before retrying. An earlier action may already have taken effect.'
    elif result['status'] == 'completed':
        next_step = 'Compare the observed answer with the requested task in the target app.'
    else:
        next_step = 'Read the stopped task in answer.md and check the target app before another attempt.'
    return {
        'title': 'Desktop task report', 'identity': 'Computer use',
        'summary': 'Task completed.' if result['status'] == 'completed' else 'Task stopped before completion.',
        'sections': [
            {'id': 'assessment', 'title': 'Assessment', 'blocks': [
                {'type': 'paragraph', 'text': answer.strip()}, {'type': 'paragraph', 'text': next_step}]},
            {'id': 'evidence', 'title': 'Evidence', 'blocks': [
                {'type': 'table', 'caption': 'Recorded actions in computer-use-audit.json',
                 'columns': ['Action number', 'Action', 'Observed outcome'], 'rows': rows}
                if rows else {'type': 'paragraph', 'text': 'The action audit contains no desktop actions.'}]},
            {'id': 'coverage', 'title': 'Coverage', 'blocks': [
                {'type': 'paragraph', 'text': 'The audit records input delivery. The answer describes the observed screen. Confirm external effects in the target app.'},
                {'type': 'paragraph', 'text': 'Screenshots, typed content and individual control values are excluded from the audit.'}]},
        ],
    }

def publish_preview(block, public, answer, audit):
    import json
    from mn_sdk.blueprint.hooks import report_activity
    from mn_sdk.blueprint.outputs import deliver_files, freeze_file_publication, merge_publications
    from mn_sdk_common.publication import ArtifactWrite

    def render():
        from mn_web_report_skill import render_report_html
        page = render_report_html(document(public, answer.decode(), json.loads(audit)))
        return [ArtifactWrite("web_report", "web/index.html", page.encode(), kind="html", required=False, mode=0o644)]

    def descriptor():
        from mn_sdk_web_ui import static_run_report_handle
        handle = static_run_report_handle(block.store.run_dir, "web/index.html", title="Desktop task report")
        return [ArtifactWrite("web_ui", "web_ui.json", json.dumps(handle).encode(), kind="json", required=False, mode=0o644)]

    try:
        page = freeze_file_publication(block, render, name="task-review-page")
        if page["warnings"] or deliver_files(block, page):
            raise OSError("Desktop task report unavailable")
        handle = freeze_file_publication(block, descriptor, name="task-review-handle")
        if handle["warnings"] or deliver_files(block, handle):
            raise OSError("Desktop task report handle unavailable")
        return merge_publications(block, page, handle)
    except Exception:
        block.check()
        report_activity("The answer and audit were saved. The web report could not be published.",
                        kind="diagnostic", level="warning", step_id=block.step_id, run_dir=block.store.run_dir)
        return None
