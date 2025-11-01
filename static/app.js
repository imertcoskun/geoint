const form = document.getElementById('upload-form');
const statusEl = document.getElementById('status');
const resultSection = document.getElementById('result');
const resultPre = document.getElementById('result-json');

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? 'status error' : 'status';
}

function showResult(data) {
  resultPre.textContent = JSON.stringify(data, null, 2);
  resultSection.hidden = false;
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById('image');
  if (!fileInput.files.length) {
    setStatus('Please choose a PNG or JPEG file to analyze.', true);
    return;
  }

  const formData = new FormData();
  formData.append('image', fileInput.files[0]);
  setStatus('Analyzing image…');
  resultSection.hidden = true;

  try {
    const response = await fetch('/analyze', {
      method: 'POST',
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      const message = payload.error || 'The analysis failed.';
      setStatus(message, true);
      return;
    }

    setStatus('Analysis complete.');
    showResult(payload);
  } catch (error) {
    console.error(error);
    setStatus('Unexpected error while analyzing the image.', true);
  }
});
