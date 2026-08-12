def render_page() -> str:
    return """<!doctype html>
<html lang="en"><body>
<form id="message-form"><label>Message <input name="message"></label><button>Save</button></form>
<p id="message" aria-live="polite"></p>
<script>
document.querySelector('#message-form').addEventListener('submit', (event) => {
  event.preventDefault();
  document.querySelector('#status').textContent = 'Saved';
});
</script>
</body></html>"""
