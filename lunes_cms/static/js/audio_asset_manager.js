document.addEventListener("DOMContentLoaded", function() {
    const config = window.audioAssetManagerConfig || {};
    const entityType = config.entityType || "entity";
    const assetType = config.assetType || "asset";
    const containerClass = config.containerClass || `${entityType}-${assetType}-container`;
    const controlsClass = config.controlsClass || `${assetType}-controls`;
    const idAttribute = config.idAttribute || `${entityType}Id`;
    const addBtnClass = config.addBtnClass || `add-${assetType}-btn`;
    const replaceBtnClass = config.replaceBtnClass || `replace-${assetType}-btn`;
    const deleteBtnClass = config.deleteBtnClass || `delete-${assetType}-btn`;
    const fileInputClass = config.fileInputClass || `${assetType}-file-input`;
    const updateEndpoint = config.updateEndpoint || `/en/admin/cmsv2/${entityType}s/\${id}/update-${assetType}/`;
    const errorMessages = config.errorMessages || {
        update: `An error occurred while updating the ${assetType}`,
        delete: `An error occurred while deleting the ${assetType}`
    };

    document.querySelectorAll(`.${containerClass}`).forEach(function(container) {
        const entityId = container.querySelector(`.${controlsClass}`).dataset[idAttribute];
        const addBtn = container.querySelector(`.${addBtnClass}`);
        const replaceBtn = container.querySelector(`.${replaceBtnClass}`);
        const deleteBtn = container.querySelector(`.${deleteBtnClass}`);
        const fileInput = container.querySelector(`.${fileInputClass}`);

        if (addBtn) {
            addBtn.addEventListener("click", function() {
                fileInput.click();
                fileInput.dataset.action = "add";
            });
        }
        
        if (replaceBtn) {
            replaceBtn.addEventListener("click", function() {
                fileInput.click();
                fileInput.dataset.action = "replace";
            });
        }
        
        if (deleteBtn) {
            deleteBtn.addEventListener("click", function() {
                if (confirm(`Are you sure you want to delete this ${assetType}?`)) {
                    deleteAsset(entityId);
                }
            });
        }
        
        if (fileInput) {
            fileInput.addEventListener("change", function() {
                if (fileInput.files.length > 0) {
                    uploadAsset(entityId, fileInput.files[0], fileInput.dataset.action, container);
                }
            });
        }
    });
    
    function uploadAsset(entityId, file, action, container) {
        const formData = new FormData();
        formData.append(assetType, file);
        formData.append("action", action);
        
        const endpoint = updateEndpoint.replace("${id}", entityId);
        
        fetch(endpoint, {
            method: "POST",
            body: formData,
            credentials: "same-origin"
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                window.location.reload();
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert(errorMessages.update);
        });
    }
    
    function deleteAsset(entityId) {
        const formData = new FormData();
        formData.append("action", "delete");
        
        const endpoint = updateEndpoint.replace("${id}", entityId);
        
        fetch(endpoint, {
            method: "POST",
            body: formData,
            credentials: "same-origin"
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                window.location.reload();
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert(errorMessages.delete);
        });
    }
});