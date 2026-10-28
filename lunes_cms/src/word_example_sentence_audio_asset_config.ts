window.audioAssetManagerConfigs = window.audioAssetManagerConfigs || []
window.audioAssetManagerConfigs.push({
    entityType: "word",
    assetType: "audio",
    containerClass: "word-example-sentence-audio-container",
    controlsClass: "example-sentence-audio-controls",
    idAttribute: "wordId",
    addBtnClass: "add-example-sentence-audio-btn",
    replaceBtnClass: "replace-example-sentence-audio-btn",
    deleteBtnClass: "delete-example-sentence-audio-btn",
    fileInputClass: "example-sentence-audio-file-input",
    updateEndpoint: "/en/admin/cmsv2/words/${id}/update-example-sentence-audio/",
    successMessages: {
        update: "Audio updated successfully",
        delete: "Audio deleted successfully",
    },
    errorMessages: {
        update: "An error occurred while updating the audio",
        delete: "An error occurred while deleting the audio",
    },
    urlResponseKey: "audio_url",
})
