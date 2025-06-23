window.audioAssetManagerConfig = {
    entityType: "word",
    assetType: "audio",
    containerClass: "word-audio-container",
    controlsClass: "audio-asset-controls",
    idAttribute: "wordId",
    addBtnClass: "add-audio-btn",
    replaceBtnClass: "replace-audio-btn",
    deleteBtnClass: "delete-audio-btn",
    fileInputClass: "audio-file-input",
    updateEndpoint: "/en/admin/cmsv2/words/${id}/update-audio/",
    successMessages: {
        update: "Audio updated successfully",
        delete: "Audio deleted successfully"
    },
    errorMessages: {
        update: "An error occurred while updating the audio",
        delete: "An error occurred while deleting the audio"
    },
    urlResponseKey: "audio_url"
}