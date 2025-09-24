window.assetManagerConfigs = window.assetManagerConfigs || []
window.assetManagerConfigs.push({
    entityType: "word",
    assetType: "image",
    containerClass: "word-image-container",
    controlsClass: "image-controls",
    idAttribute: "wordId",
    addBtnClass: "add-image-btn",
    replaceBtnClass: "replace-image-btn",
    deleteBtnClass: "delete-image-btn",
    fileInputClass: "image-file-input",
    updateEndpoint: "/en/admin/cmsv2/words/${id}/update-image/",
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