// Camera functionality for attendee selfie
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const eventCodeInput = document.getElementById('eventCode');
    const checkEventBtn = document.getElementById('checkEventBtn');
    const cameraSection = document.getElementById('cameraSection');
    const cameraPreview = document.getElementById('cameraPreview');
    const photoCanvas = document.getElementById('photoCanvas');
    const captureBtn = document.getElementById('captureBtn');
    const retakeBtn = document.getElementById('retakeBtn');
    const photoPreview = document.getElementById('photoPreview');
    const capturedPhoto = document.getElementById('capturedPhoto');
    const usePhotoBtn = document.getElementById('usePhotoBtn');
    const resultsSection = document.getElementById('resultsSection');
    const gallery = document.getElementById('gallery');
    const photoCount = document.getElementById('photoCount');
    const resultsMessage = document.getElementById('resultsMessage');
    const viewMoreBtn = document.getElementById('viewMoreBtn');
    const downloadAllBtn = document.getElementById('downloadAllBtn');
    const newSearchBtn = document.getElementById('newSearchBtn');
    const eventCheckResult = document.getElementById('eventCheckResult');
    
    // Variables
    let stream = null;
    let capturedPhotoData = null;
    let currentEventCode = '';
    let currentUserId = '';
    let currentPhotos = [];
    let displayedPhotos = 0;
    const PHOTOS_PER_LOAD = 20;
    
    // Check event code
    checkEventBtn.addEventListener('click', async function() {
        const eventCode = eventCodeInput.value.trim().toUpperCase();
        
        if (!eventCode) {
            showError('Please enter an event code');
            return;
        }
        
        checkEventBtn.disabled = true;
        checkEventBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';
        
        try {
            // Check if event exists
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ check_event: true, event_code: eventCode })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                currentEventCode = eventCode;
                document.querySelector('.login-section').classList.add('hidden');
                cameraSection.classList.remove('hidden');
                startCamera();
            } else {
                showError(data.message || 'Event not found. Please check the code.');
            }
        } catch (error) {
            showError('Network error. Please try again.');
            console.error('Error:', error);
        } finally {
            checkEventBtn.disabled = false;
            checkEventBtn.innerHTML = '<i class="fas fa-arrow-right"></i> Continue';
        }
    });
    
    // Start camera
    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'user',
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                },
                audio: false 
            });
            
            cameraPreview.srcObject = stream;
            captureBtn.disabled = false;
        } catch (error) {
            console.error('Camera error:', error);
            showError('Could not access camera. Please ensure camera permissions are granted.');
        }
    }
    
    // Capture photo
    captureBtn.addEventListener('click', function() {
        // Set canvas dimensions to match video
        photoCanvas.width = cameraPreview.videoWidth;
        photoCanvas.height = cameraPreview.videoHeight;
        
        // Draw video frame to canvas
        const context = photoCanvas.getContext('2d');
        context.drawImage(cameraPreview, 0, 0, photoCanvas.width, photoCanvas.height);
        
        // Get image data
        capturedPhotoData = photoCanvas.toDataURL('image/jpeg');
        capturedPhoto.src = capturedPhotoData;
        
        // Show preview, hide camera
        cameraPreview.classList.add('hidden');
        captureBtn.classList.add('hidden');
        photoPreview.classList.remove('hidden');
        retakeBtn.classList.remove('hidden');
    });
    
    // Retake photo
    retakeBtn.addEventListener('click', function() {
        capturedPhotoData = null;
        capturedPhoto.src = '';
        
        cameraPreview.classList.remove('hidden');
        captureBtn.classList.remove('hidden');
        photoPreview.classList.add('hidden');
        retakeBtn.classList.add('hidden');
    });
    
    // Use photo to find matches
    usePhotoBtn.addEventListener('click', async function() {
        usePhotoBtn.disabled = true;
        usePhotoBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Finding your photos...';
        
        try {
            // Convert data URL to blob
            const blob = dataURLtoBlob(capturedPhotoData);
            const formData = new FormData();
            formData.append('event_code', currentEventCode);
            formData.append('selfie', blob, 'selfie.jpg');
            
            // Send to server
            const response = await fetch('/api/login', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                if (data.matched) {
                    currentUserId = data.user_id;
                    currentPhotos = data.photo_urls || [];
                    
                    // Show results
                    cameraSection.classList.add('hidden');
                    resultsSection.classList.remove('hidden');
                    
                    // Update UI
                    photoCount.textContent = `(${currentPhotos.length})`;
                    resultsMessage.innerHTML = `
                        <div class="success-box">
                            <h3><i class="fas fa-check-circle"></i> Success!</h3>
                            <p>We found <strong>${currentPhotos.length} photos</strong> of you in this event.</p>
                            <p>Confidence: <strong>${(data.confidence * 100).toFixed(1)}%</strong></p>
                        </div>
                    `;
                    
                    // Display photos
                    displayPhotos();
                    
                    // Show buttons if there are photos
                    if (currentPhotos.length > 0) {
                        if (currentPhotos.length > PHOTOS_PER_LOAD) {
                            viewMoreBtn.classList.remove('hidden');
                        }
                        downloadAllBtn.classList.remove('hidden');
                    }
                } else {
                    // No match found
                    resultsMessage.innerHTML = `
                        <div class="warning">
                            <h3><i class="fas fa-exclamation-triangle"></i> No Match Found</h3>
                            <p>${data.message || "We couldn't find any photos matching your face."}</p>
                            <p>Try: Taking a clearer photo with good lighting, removing sunglasses, or checking if you're in the event photos.</p>
                        </div>
                    `;
                    cameraSection.classList.add('hidden');
                    resultsSection.classList.remove('hidden');
                }
            } else {
                showError(data.message || 'An error occurred');
            }
        } catch (error) {
            showError('Network error. Please try again.');
            console.error('Error:', error);
        } finally {
            usePhotoBtn.disabled = false;
            usePhotoBtn.innerHTML = 'Yes, Find My Photos!';
        }
    });
    
    // Display photos in gallery
    function displayPhotos() {
        const endIndex = Math.min(displayedPhotos + PHOTOS_PER_LOAD, currentPhotos.length);
        
        for (let i = displayedPhotos; i < endIndex; i++) {
            const photoUrl = currentPhotos[i];
            
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            photoItem.innerHTML = `
                <img src="${photoUrl}" alt="Your photo ${i + 1}" loading="lazy">
                <input type="checkbox" class="photo-checkbox" data-index="${i}" checked>
                <a href="${photoUrl}" download="photo_${i + 1}.jpg" 
                   style="position: absolute; bottom: 10px; left: 10px; background: rgba(0,0,0,0.7); color: white; padding: 5px 10px; border-radius: 5px; text-decoration: none;">
                    <i class="fas fa-download"></i>
                </a>
            `;
            
            gallery.appendChild(photoItem);
        }
        
        displayedPhotos = endIndex;
        
        // Hide "View More" if all photos are displayed
        if (displayedPhotos >= currentPhotos.length) {
            viewMoreBtn.classList.add('hidden');
        }
    }
    
    // View more photos
    viewMoreBtn.addEventListener('click', function() {
        displayPhotos();
    });
    
    // Download all selected photos
    downloadAllBtn.addEventListener('click', async function() {
        // Simple implementation: open each photo in new tab
        // Note: Browsers may block multiple popups
        const checkboxes = document.querySelectorAll('.photo-checkbox:checked');
        
        if (checkboxes.length === 0) {
            alert('Please select at least one photo to download');
            return;
        }
        
        downloadAllBtn.disabled = true;
        downloadAllBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Preparing download...';
        
        // Download each selected photo
        for (const checkbox of checkboxes) {
            const index = parseInt(checkbox.dataset.index);
            const photoUrl = currentPhotos[index];
            
            // Create hidden link and trigger download
            const link = document.createElement('a');
            link.href = photoUrl;
            link.download = `grabpic_photo_${index + 1}.jpg`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Small delay between downloads
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        downloadAllBtn.disabled = false;
        downloadAllBtn.innerHTML = '<i class="fas fa-download"></i> Download All';
        
        alert(`Downloaded ${checkboxes.length} photos. Check your downloads folder.`);
    });
    
    // New search
    newSearchBtn.addEventListener('click', function() {
        // Reset everything
        currentEventCode = '';
        currentUserId = '';
        currentPhotos = [];
        displayedPhotos = 0;
        
        // Stop camera
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        
        // Reset UI
        resultsSection.classList.add('hidden');
        cameraSection.classList.add('hidden');
        document.querySelector('.login-section').classList.remove('hidden');
        eventCodeInput.value = '';
        gallery.innerHTML = '';
        photoPreview.classList.add('hidden');
        cameraPreview.classList.remove('hidden');
        captureBtn.classList.remove('hidden');
        retakeBtn.classList.add('hidden');
    });
    
    // Helper functions
    function showError(message) {
        eventCheckResult.innerHTML = `
            <div class="error-box">
                <i class="fas fa-exclamation-circle"></i> ${message}
            </div>
        `;
        eventCheckResult.classList.remove('hidden');
    }
    
    function dataURLtoBlob(dataURL) {
        const arr = dataURL.split(',');
        const mime = arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        
        return new Blob([u8arr], { type: mime });
    }
    
    // Clean up camera on page unload
    window.addEventListener('beforeunload', function() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    });
});