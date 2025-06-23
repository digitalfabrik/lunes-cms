window.assetManagerConfigs = window.assetManagerConfigs || []
window.assetManagerConfigs.push({
    entityType: "job",
    assetType: "icon",
    containerClass: "job-icon-container",
    controlsClass: "icon-controls",
    idAttribute: "jobId",
    addBtnClass: "add-icon-btn",
    replaceBtnClass: "replace-icon-btn",
    deleteBtnClass: "delete-icon-btn",
    fileInputClass: "icon-file-input",
    updateEndpoint: "/en/admin/cmsv2/jobs/${id}/update-icon/",
    successMessages: {
        update: "Icon updated successfully",
        delete: "Icon deleted successfully"
    },
    errorMessages: {
        update: "An error occurred while updating the icon",
        delete: "An error occurred while deleting the icon"
    },
    urlResponseKey: "icon_url"
})