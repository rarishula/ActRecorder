(function() {
    const dbName = "TestDB";
    const storeName = "KeyValueStore";

    window.openDatabase = function(callback) {
        const request = indexedDB.open(dbName, 2); // 明示的にバージョン2

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(storeName)) {
                db.createObjectStore(storeName);
                console.log(`ObjectStore '${storeName}' created.`);
            }
        };

        request.onsuccess = (event) => {
            const db = event.target.result;
            callback(null, db);
        };

        request.onerror = (event) => {
            callback(event.target.error, null);
        };
    };

    window.saveToIndexedDB = function(key, value, callback) {
        openDatabase((error, db) => {
            if (error) {
                callback(error);
                return;
            }

            const transaction = db.transaction(storeName, "readwrite");
            const store = transaction.objectStore(storeName);
            store.put(value, key);

            transaction.oncomplete = () => {
                callback(null, "保存しました");
            };

            transaction.onerror = (event) => {
                callback(event.target.error);
            };
        });
    };

    window.loadFromIndexedDB = function(key, callback) {
        openDatabase((error, db) => {
            if (error) {
                callback(error, null);
                return;
            }

            const transaction = db.transaction(storeName, "readonly");
            const store = transaction.objectStore(storeName);

            const request = store.get(key);
            request.onsuccess = () => {
                callback(null, request.result);
            };

            request.onerror = (event) => {
                callback(event.target.error, null);
            };
        });
    };
})();
