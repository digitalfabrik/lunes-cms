var cacheName = 'v1:static';

self.addEventListener('install', function(e) {
    e.waitUntil(
        caches.open(cacheName).then(function(cache) {
            return cache.addAll([
                './static/style.css',
                './static/scripts.js',
                './static/jquery.min.js',
                './static/favicon.png',
                './static/bootstrap/css/bootstrap.min.css',
                './static/bootstrap/js/bootstrap.min.js'
            ]).then(function() {
                self.skipWaiting();
            });
        })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request).then(function(response) {
            if (response) {
                return response;
            }
            return fetch(event.request);
        })
    );
});
