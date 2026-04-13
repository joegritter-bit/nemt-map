// Ensure the PDF.js worker is configured.
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';

// Global variables
let originalPdfArrayBuffer = null;
let currentPdf = null;
let fieldCounter = 0;

const pdfUpload = document.getElementById('pdf-upload');
const downloadPdfBtn = document.getElementById('download-pdf');
const fillWithGeminiBtn = document.getElementById('fill-gemini');
const inputLayer = document.getElementById('input-layer');
const canvas = document.getElementById('pdf-render');
const ctx = canvas.getContext('2d');

// 1. Listen for PDF upload and render the first page
pdfUpload.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
        const reader = new FileReader();
        reader.onload = async (e) => {
            originalPdfArrayBuffer = e.target.result;
            inputLayer.innerHTML = ''; // Clear previous inputs
            fieldCounter = 0; // Reset counter for new PDF
            await renderPdf(originalPdfArrayBuffer);
        };
        reader.readAsArrayBuffer(file);
    }
});

async function renderPdf(data) {
    currentPdf = await pdfjsLib.getDocument({ data }).promise;
    const page = await currentPdf.getPage(1);
    const viewport = page.getViewport({ scale: 1.5 });

    canvas.height = viewport.height;
    canvas.width = viewport.width;
    inputLayer.style.width = `${canvas.width}px`;
    inputLayer.style.height = `${canvas.height}px`;

    const renderContext = {
        canvasContext: ctx,
        viewport: viewport
    };
    await page.render(renderContext).promise;
}

// 2. Create named and positioned inputs on click
inputLayer.addEventListener('click', (event) => {
    if (currentPdf && event.target === inputLayer) {
        fieldCounter++;
        const input = document.createElement('input');
        input.type = 'text';
        input.name = `field_${fieldCounter}`;
        input.style.left = `${event.offsetX}px`;
        input.style.top = `${event.offsetY}px`;
        inputLayer.appendChild(input);
        input.focus();
    }
});

// 3. Placeholder 'Fill with Gemini' function
fillWithGeminiBtn.addEventListener('click', () => {
    const textInputs = inputLayer.querySelectorAll('input[type="text"]');
    if (textInputs.length === 0) {
        console.log('No fields to fill. Click on the PDF to add fields.');
        return;
    }
    const fieldNames = Array.from(textInputs).map(input => input.name);
    console.log('Detected form fields:', fieldNames);
    // In a real scenario, you would pass these field names to a generative AI
    // to get relevant values, and then populate the input fields.
});

// 4. Download the PDF with embedded text
downloadPdfBtn.addEventListener('click', async () => {
    if (!originalPdfArrayBuffer) {
        alert('Please upload a PDF first!');
        return;
    }

    const { PDFDocument } = PDFLib;
    const pdfDoc = await PDFDocument.load(originalPdfArrayBuffer);
    const firstPage = pdfDoc.getPages()[0];
    const { width: pdfWidth, height: pdfHeight } = firstPage.getSize();
    const { width: canvasWidth, height: canvasHeight } = canvas;
    
    const ScaleX = pdfWidth / canvasWidth;
    const ScaleY = pdfHeight / canvasHeight;

    const textInputs = inputLayer.querySelectorAll('input[type="text"]');

    textInputs.forEach(input => {
        const text = input.value;
        if (text) {
            const InputX = parseFloat(input.style.left);
            const InputY = parseFloat(input.style.top);
            
            const FinalX = InputX * ScaleX;
            // This formula flips the Y-axis and adjusts for font height
            const FinalY = pdfHeight - (InputY * ScaleY) - 10; 

            firstPage.drawText(text, {
                x: FinalX,
                y: FinalY,
                size: 10, // Using a fixed size for simplicity
            });
        }
    });

    const pdfBytes = await pdfDoc.save();
    const blob = new Blob([pdfBytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'filled_document.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});
