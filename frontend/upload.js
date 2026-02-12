// Upload functionality for organizer
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const eventNameInput = document.getElementById('eventName');
    const organizerNameInput = document.getElementById('organizerName');
    const createEventBtn = document.getElementById('createEventBtn');
    const eventCreatedDiv = document.getElementById('eventCreated');
    const eventCodeDisplay = document.getElementById('eventCodeDisplay');
    const uploadSection = document.getElementById('uploadSection');
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const accessCodeInput = document.getElementById('accessCode');
    const eventIdInput = document.getElementById('eventId');
    const fileList = document.getElementById('fileList');
    const uploadBtn = document.getElementById('uploadBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const uploadStatus = document.getElementById('uploadStatus');
    
    // Variables
    let selectedFiles = [];
    let currentEventId = '';
    let currentAccessCode = '';
    
    // Create event
    createEventBtn.addEventListener('click', async function() {
        const eventName = eventNameInput.value.trim();
        const organizerName = organizerNameInput.value.trim();
        
        if (!eventName || !organizerName) {
            alert('Please fill in all fields');
            return;
        }
        
        createEventBtn.disabled = true;
        createEventBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
        
        try {
            const response = await fetch('/api/create_event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    event_name: eventName,
                    organizer_name: organizerName
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                currentEventId = data.event_id;
                currentAccessCode = data.access_code;
                
                // Show success message
                eventCodeDisplay.textContent = currentAccessCode;
                eventCreatedDiv.classList.remove('hidden');
                
                // Show upload section
                uploadSection.style.display = 'block';
                accessCodeInput.value = currentAccessCode;
                eventIdInput.value = currentEventId;
                
                // Scroll to upload section
                uploadSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                alert('Error: ' + data.message);
            }
        } catch (error) {
            alert('Network error. Please try again.');
            console.error('Error:', error);
        } finally {
            createEventBtn.disabled = false;
            createEventBtn.innerHTML = '<i class="fas fa-plus-circle"></i> Create Event';
        }
    });
    
    // File selection via click
    dropArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    // File selection via input
    fileInput.addEventListener('change', function(e) {
        handleFiles(e.target.files);
    });
    
    // Drag and drop
    dropArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropArea.style.borderColor = '#6c8bc7';
        dropArea.style.background = '#f8fafd';
    });
    
    dropArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dropArea.style.borderColor = '#ddd';
        dropArea.style.background = '';
    });
    
    dropArea.addEventListener('drop', function(e) {
        e.preventDefault();
        dropArea.style.borderColor = '#ddd';
        dropArea.style.background = '';
        
        const files = e.dataTransfer.files;
        handleFiles(files);
    });
    
    // Handle selected files
    function handleFiles(files) {
        const newFiles = Array.from(files).filter(file => {
            // Check file type
            const extension = file.name.split('.').pop().toLowerCase();
            const allowedExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp'];
            
            if (!allowedExtensions.includes(extension)) {
                alert(`File ${file.name} has unsupported format. Skipping.`);
                return false;
            }
            
            // Check file size (max 10MB)
            if (file.size > 10 * 1024 * 1024) {
                alert(`File ${file.name} is too large (max 10MB). Skipping.`);
                return false;
            }
            
            return true;
        });
        
        // Add to selected files
        selectedFiles.push(...newFiles);
        updateFileList();
        
        // Enable upload button
        if (selectedFiles.length > 0 && accessCodeInput.value.trim()) {
            uploadBtn.disabled = false;
        }
    }
    
    // Update file list display
    function updateFileList() {
        fileList.innerHTML = '';
        
        if (selectedFiles.length === 0) {
            fileList.innerHTML = '<p style="text-align: center; color: #666;">No files selected</p>';
            return;
        }
        
        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            const fileSize = formatFileSize(file.size);
            
            fileItem.innerHTML = `
                <span class="file-name">${file.name}</span>
                <span class="file-size">${fileSize}</span>
                <button class="remove-file" data-index="${index}" style="background: none; border: none; color: #f44336; cursor: pointer;">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            fileList.appendChild(fileItem);
        });
        
        // Add event listeners to remove buttons
        document.querySelectorAll('.remove-file').forEach(button => {
            button.addEventListener('click', function() {
                const index = parseInt(this.dataset.index);
                selectedFiles.splice(index, 1);
                updateFileList();
                
                if (selectedFiles.length === 0) {
                    uploadBtn.disabled = true;
                }
            });
        });
    }
    
    // Upload files
    uploadBtn.addEventListener('click', async function() {
        const accessCode = accessCodeInput.value.trim();
        const eventId = eventIdInput.value.trim();
        
        if (!accessCode) {
            alert('Please enter the access code');
            return;
        }
        
        if (selectedFiles.length === 0) {
            alert('Please select at least one photo');
            return;
        }
        
        // Disable UI
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
        progressContainer.classList.remove('hidden');
        progressFill.style.width = '0%';
        progressText.textContent = 'Starting upload...';
        
        // Create FormData
        const formData = new FormData();
        formData.append('event_id', eventId);
        formData.append('access_code', accessCode);
        
        // Add files
        selectedFiles.forEach(file => {
            formData.append('photos', file);
        });
        
        try {
            const response = await fetch('/api/upload_photos', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                progressFill.style.width = '100%';
                progressText.textContent = 'Upload complete! Starting face processing...';
                
                // Start polling for processing status
                const processingId = data.processing_id;
                pollProcessingStatus(processingId);
                
                uploadStatus.innerHTML = `
                    <div class="success-box">
                        <h3><i class="fas fa-check-circle"></i> Upload Successful!</h3>
                        <p>${selectedFiles.length} photos uploaded. Now processing faces...</p>
                        <p>Processing ID: <code>${processingId}</code></p>
                    </div>
                `;
                uploadStatus.classList.remove('hidden');
                
                // Clear file selection
                selectedFiles = [];
                updateFileList();
                fileInput.value = '';
                
            } else {
                throw new Error(data.message || 'Upload failed');
            }
        } catch (error) {
            uploadStatus.innerHTML = `
                <div class="error-box">
                    <i class="fas fa-exclamation-circle"></i> Upload failed: ${error.message}
                </div>
            `;
            uploadStatus.classList.remove('hidden');
            
            progressText.textContent = 'Upload failed';
            progressFill.style.backgroundColor = '#f44336';
        } finally {
            uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload Photos';
        }
    });
    
    // Poll for processing status
    async function pollProcessingStatus(processingId) {
        let attempts = 0;
        const maxAttempts = 300; // 5 minutes at 1-second intervals
        
        const poll = async () => {
            try {
                const response = await fetch(`/api/processing_status/${processingId}`);
                const data = await response.json();
                
                if (data.status === 'completed') {
                    progressText.textContent = 'Processing complete!';
                    uploadStatus.innerHTML = `
                        <div class="success-box">
                            <h3><i class="fas fa-check-circle"></i> Processing Complete!</h3>
                            <p>Found ${data.total_faces} faces belonging to ${data.unique_people} unique people.</p>
                            <p>Attendees can now use the event code <strong>${currentAccessCode}</strong> to find their photos.</p>
                        </div>
                    `;
                    return; // Stop polling
                } else if (data.status === 'failed') {
                    progressText.textContent = 'Processing failed';
                    progressFill.style.backgroundColor = '#f44336';
                    uploadStatus.innerHTML += `
                        <div class="error-box">
                            <i class="fas fa-exclamation-circle"></i> Processing failed: ${data.error}
                        </div>
                    `;
                    return; // Stop polling
                } else {
                    // Update progress
                    const processed = data.processed_photos || 0;
                    const total = data.total_photos || 1;
                    const percent = Math.min(100, Math.round((processed / total) * 100));
                    
                    progressFill.style.width = `${percent}%`;
                    progressText.textContent = `Processing: ${processed}/${total} photos (${percent}%)`;
                    
                    // Continue polling
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(poll, 1000); // Poll every second
                    }
                }
            } catch (error) {
                console.error('Error polling status:', error);
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, 1000);
                }
            }
        };
        
        // Start polling
        poll();
    }
    
    // Helper function to format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
});