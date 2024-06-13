"""
This modules contains the config for the API tests
"""

#: The disciplines endpoints
DISCIPLINE_ENDPOINTS = [
    {
        "endpoint": "/api/disciplines/",
        "expected_result": "tests/api/expected-results/disciplines.json",
    },
    {
        "endpoint": "/api/disciplines/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/disciplines_by_key.json",
    },
    {
        "endpoint": "/api/disciplines/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/disciplines/15/",
        "expected_result": "tests/api/expected-results/disciplines_15.json",
    },
    {
        "endpoint": "/api/disciplines/15/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/not_found.json",
        "expected_status_code": 404,
    },
    {
        "endpoint": "/api/disciplines/15/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/disciplines/20/",
        "expected_result": "tests/api/expected-results/not_found.json",
        "expected_status_code": 404,
    },
    {
        "endpoint": "/api/disciplines/20/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/disciplines_20.json",
    },
    {
        "endpoint": "/api/disciplines/20/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/disciplines/1/",
        "expected_result": "tests/api/expected-results/not_found.json",
        "expected_status_code": 404,
    },
    {
        "endpoint": "/api/disciplines_by_level/",
        "expected_result": "tests/api/expected-results/disciplines_by_level.json",
    },
    {
        "endpoint": "/api/disciplines_by_level/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/disciplines_by_level.json",
    },
    {
        "endpoint": "/api/disciplines_by_level/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/disciplines_by_level.json",
    },
    {
        "endpoint": "/api/disciplines_by_level/27/",
        "expected_result": "tests/api/expected-results/disciplines_by_level_27.json",
    },
    {
        "endpoint": "/api/disciplines_by_level/27/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/disciplines_by_level_27.json",
    },
    {
        "endpoint": "/api/disciplines_by_level/27/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/disciplines_by_level_27.json",
    },
    {
        "endpoint": "/api/disciplines_by_level/48/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/disciplines_by_level_48.json",
    },
    {
        "endpoint": "/api/disciplines_by_level/48/",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/disciplines_by_level/48/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/disciplines_by_group/1/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/disciplines_by_group.json",
    },
    {
        "endpoint": "/api/disciplines_by_group/1/",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/disciplines_by_group/1/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
]

#: The training set endpoints
TRAINING_SET_ENDPOINTS = [
    {
        "endpoint": "/api/training_sets/",
        "expected_result": "tests/api/expected-results/training_sets.json",
    },
    {
        "endpoint": "/api/training_sets/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/training_sets_by_key.json",
    },
    {
        "endpoint": "/api/training_sets/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/training_sets/7/",
        "expected_result": "tests/api/expected-results/training_sets_7.json",
    },
    {
        "endpoint": "/api/training_sets/7/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/not_found.json",
        "expected_status_code": 404,
    },
    {
        "endpoint": "/api/training_sets/7/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/training_sets/108/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/training_sets_108.json",
    },
    {
        "endpoint": "/api/training_sets/108/",
        "expected_result": "tests/api/expected-results/not_found.json",
        "expected_status_code": 404,
    },
    {
        "endpoint": "/api/training_sets/108/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/training_set/15/",
        "expected_result": "tests/api/expected-results/training_sets_by_discipline_15.json",
    },
    {
        "endpoint": "/api/training_set/15/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/training_sets_by_discipline_15.json",
    },
    {
        "endpoint": "/api/training_set/15/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/training_sets_by_discipline_15.json",
    },
    {
        "endpoint": "/api/training_set/20/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/training_sets_by_discipline_20.json",
    },
    {
        "endpoint": "/api/training_set/20/",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/training_set/20/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
]

#: The vocabulary word endpoints
VOCABULARY_ENDPOINTS = [
    {
        "endpoint": "/api/documents/7/",
        "expected_result": "tests/api/expected-results/documents_by_training_set_7.json",
    },
    {
        "endpoint": "/api/documents/7/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/documents_by_training_set_7.json",
    },
    {
        "endpoint": "/api/documents/7/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/documents_by_training_set_7.json",
    },
    {
        "endpoint": "/api/documents/108/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/documents_by_training_set_108.json",
    },
    {
        "endpoint": "/api/documents/108/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/documents/108/",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/document_by_id/1/",
        "expected_result": "tests/api/expected-results/not_authenticated.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/words/",
        "expected_result": "tests/api/expected-results/words.json",
    },
    {
        "endpoint": "/api/words/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/words_by_key.json",
    },
    {
        "endpoint": "/api/words/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/words/2/",
        "expected_result": "tests/api/expected-results/words_2.json",
    },
    {
        "endpoint": "/api/words/2/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/words_2.json",
    },
    {
        "endpoint": "/api/words/2/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/words/170/",
        "expected_result": "tests/api/expected-results/not_found.json",
        "expected_status_code": 404,
    },
    {
        "endpoint": "/api/words/170/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/words_170.json",
    },
    {
        "endpoint": "/api/words/170/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
]

#: The group endpoints
GROUP_ENDPOINTS = [
    {
        "endpoint": "/api/group_info/",
        "api_key": "VALIDTOKEN",
        "expected_result": "tests/api/expected-results/group_info.json",
    },
    {
        "endpoint": "/api/group_info/",
        "api_key": "INVALIDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/group_info/",
        "expected_result": "tests/api/expected-results/not_authenticated.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/group_info/",
        "api_key": "EXPIREDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
    {
        "endpoint": "/api/group_info/",
        "api_key": "REVOKEDTOKEN",
        "expected_result": "tests/api/expected-results/permission_denied.json",
        "expected_status_code": 403,
    },
]

#: The feedback endpoints
FEEDBACK_ENDPOINTS = [
    {
        "endpoint": "/api/feedback/",
        "post_data": {
            "comment": "Schneidig!",
            "content_type": "document",
            "object_id": 2,
        },
        "expected_result": "tests/api/expected-results/feedback_document.json",
        "expected_status_code": 201,
    },
    {
        "endpoint": "/api/feedback/",
        "post_data": {
            "comment": "Spannend!",
            "content_type": "trainingset",
            "object_id": 7,
        },
        "expected_result": "tests/api/expected-results/feedback_training_set.json",
        "expected_status_code": 201,
    },
    {
        "endpoint": "/api/feedback/",
        "post_data": {
            "comment": "Lecker!",
            "content_type": "discipline",
            "object_id": 15,
        },
        "expected_result": "tests/api/expected-results/feedback_discipline.json",
        "expected_status_code": 201,
    },
    {
        "endpoint": "/api/feedback/",
        "post_data": {"comment": "invalid", "content_type": "invalid", "object_id": 1},
        "expected_result": "tests/api/expected-results/feedback_invalid_content_type.json",
        "expected_status_code": 400,
    },
    {
        "endpoint": "/api/feedback/",
        "post_data": {
            "comment": "not existing",
            "content_type": "document",
            "object_id": 1,
        },
        "expected_result": "tests/api/expected-results/feedback_document_not_found.json",
        "expected_status_code": 400,
    },
]


#: The sponsor endpoints
SPONSOR_ENDPOINTS = [
    {
        "endpoint": "/api/sponsors/",
        "expected_result": "tests/api/expected-results/sponsors.json",
    },
    {
        "endpoint": "/api/sponsors/1",
        "expected_result": "tests/api/expected-results/sponsors_1.json",
    },
    {
        "endpoint": "/api/sponsors/2",
        "expected_result": "tests/api/expected-results/sponsors_2.json",
    },
    {
        "endpoint": "/api/sponsors/3",
        "expected_result": "tests/api/expected-results/not_found.json",
        "expected_status_code": 404,
    },
]


SEARCH_DUPLICATE_ENDPOINTS = [
    {
        "endpoint": "/api/search_duplicate/implementieren",
        "expected_result": "tests/api/expected-results/duplicate_implementieren.json",
    },
    {
        "endpoint": "/api/search_duplicate/Schere",
        "expected_result": "tests/api/expected-results/duplicate_Schere.json",
    },
    {
        "endpoint": "/api/search_duplicate/Ei",
        "expected_result": "tests/api/expected-results/duplicate_Ei.json",
    },
    {
        "endpoint": "/api/search_duplicate/neueswort",
        "expected_result": "tests/api/expected-results/duplicate_neueswort.json",
    },
]

#: The API endpoints
API_ENDPOINTS = (
    DISCIPLINE_ENDPOINTS
    + TRAINING_SET_ENDPOINTS
    + VOCABULARY_ENDPOINTS
    + GROUP_ENDPOINTS
    + FEEDBACK_ENDPOINTS
    + SPONSOR_ENDPOINTS
    + SEARCH_DUPLICATE_ENDPOINTS
)

#: Convert the dicts to tuples with a fixed length
PARAMETRIZED_API_ENDPOINTS = [
    (
        config.get("endpoint"),
        config.get("post_data"),
        config.get("api_key"),
        config.get("expected_result"),
        config.get("expected_status_code", 200),
    )
    for config in API_ENDPOINTS
]
