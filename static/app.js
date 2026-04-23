document.addEventListener('DOMContentLoaded', () => {
    const inputText = document.getElementById('input-text');
    const processBtn = document.getElementById('process-btn');
    const clearBtn = document.getElementById('clear-btn');
    const copyBtn = document.getElementById('copy-btn');
    const outputSection = document.getElementById('output-section');
    const outputText = document.getElementById('output-text');
    const loader = document.getElementById('loader');
    const btnText = document.getElementById('btn-text');
    const toast = document.getElementById('toast');

    processBtn.addEventListener('click', async () => {
        const text = inputText.value.trim();
        if (!text) return;

        // Set UI to loading state
        processBtn.disabled = true;
        loader.style.display = 'block';
        btnText.style.opacity = '0.5';

        try {
            const response = await fetch('/api/stress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });

            if (!response.ok) {
                throw new Error('Ошибка сервера');
            }

            const data = await response.json();
            
            // Show result
            outputText.textContent = data.processed;
            outputSection.style.display = 'block';
            
            // Scroll to output
            outputSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (error) {
            console.error('Error:', error);
            alert('Произошла ошибка при обработке текста. Пожалуйста, попробуйте позже.');
        } finally {
            // Restore UI state
            processBtn.disabled = false;
            loader.style.display = 'none';
            btnText.style.opacity = '1';
        }
    });

    clearBtn.addEventListener('click', () => {
        inputText.value = '';
        outputSection.style.display = 'none';
        inputText.focus();
    });

    copyBtn.addEventListener('click', () => {
        const text = outputText.textContent;
        navigator.clipboard.writeText(text).then(() => {
            showToast();
        });
    });

    function showToast() {
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 2000);
    }
});
