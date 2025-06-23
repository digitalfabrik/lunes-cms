window.assetManagerConfigs = window.assetManagerConfigs || []
window.assetManagerConfigs.push({
    entityType: "unitword",
    assetType: "image",
    containerClass: "unitword-image-container",
    controlsClass: "unitword-image-controls",
    idAttribute: "unitwordId",
    addBtnClass: "add-unitword-image-btn",
    replaceBtnClass: "replace-unitword-image-btn",
    deleteBtnClass: "delete-unitword-image-btn",
    fileInputClass: "unitword-image-file-input",
    updateEndpoint: "/en/admin/cmsv2/unitwordrelations/${id}/update-image/",
    successMessages: {
        update: "Image updated successfully",
        delete: "Image deleted successfully"
    },
    errorMessages: {
        update: "An error occurred while updating the image",
        delete: "An error occurred while deleting the image"
    },
    urlResponseKey: "image_url"
})