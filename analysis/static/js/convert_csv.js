/**
 * ULG to CSV Conversion Handler
 */

document.addEventListener('DOMContentLoaded', function() {
    const csvForm = document.getElementById('csvConversionForm');
    const ulgFileInput = document.getElementById('ulg_file_csv');
    const convertBtn = document.getElementById('convertCsvBtn');
    const convertBtnText = document.getElementById('convertBtnText');
    const convertBtnLoading = document.getElementById('convertBtnLoading');
    const resultDiv = document.getElementById('csvConversionResult');

    // File drop zone handler
    const ulgDropZone = document.getElementById('ulgFileCsvZone');
    const ulgFileName = ulgDropZone.querySelector('.file-name');

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        ulgDropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        ulgDropZone.addEventListener(eventName, () => {
            ulgDropZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        ulgDropZone.addEventListener(eventName, () => {
            ulgDropZone.classList.remove('drag-over');
        });
    });

    ulgDropZone.addEventListener('drop', handleDrop);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        ulgFileInput.files = files;
        updateFileName();
    }

    // File input change handler
    ulgFileInput.addEventListener('change', updateFileName);

    function updateFileName() {
        if (ulgFileInput.files.length > 0) {
            const fileName = ulgFileInput.files[0].name;
            ulgFileName.textContent = `선택된 파일: ${fileName}`;
            ulgFileName.style.color = '#10b981';
            ulgFileName.style.fontWeight = '600';
        }
    }

    // Form submission
    csvForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Validate file
        if (ulgFileInput.files.length === 0) {
            showResult('ULG 파일을 선택해주세요.', 'error');
            return;
        }

        const file = ulgFileInput.files[0];
        if (!file.name.endsWith('.ulg')) {
            showResult('ULG 파일만 업로드 가능합니다.', 'error');
            return;
        }

        // Show loading state
        convertBtn.disabled = true;
        convertBtnText.classList.add('hidden');
        convertBtnLoading.classList.remove('hidden');

        // Prepare form data
        const formData = new FormData();
        formData.append('ulg_file', file);

        const sessionId = document.getElementById('session_id_input').value;
        const aircraftId = document.getElementById('aircraft_id_input').value || 'UMT001';

        if (sessionId) {
            formData.append('session_id', sessionId);
        }
        formData.append('aircraft_id', aircraftId);

        try {
            // Send conversion request
            const response = await fetch('/convert-to-csv', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '변환 중 오류가 발생했습니다.');
            }

            // Get the blob
            const blob = await response.blob();

            // Get filename from Content-Disposition header or generate one
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'converted.csv';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Show success message
            showResult(`✅ 변환 완료! 파일이 다운로드되었습니다: ${filename}`, 'success');

            // Reset form
            csvForm.reset();
            ulgFileName.textContent = '';

        } catch (error) {
            console.error('Error:', error);
            showResult(`❌ 오류: ${error.message}`, 'error');
        } finally {
            // Reset button state
            convertBtn.disabled = false;
            convertBtnText.classList.remove('hidden');
            convertBtnLoading.classList.add('hidden');
        }
    });

    function showResult(message, type) {
        resultDiv.textContent = message;
        resultDiv.className = type;
        resultDiv.classList.remove('hidden');

        // Auto-hide success messages after 10 seconds
        if (type === 'success') {
            setTimeout(() => {
                resultDiv.classList.add('hidden');
            }, 10000);
        }
    }
});
