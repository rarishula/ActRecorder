document.addEventListener("DOMContentLoaded", function() {
    const messageElement = document.getElementById("message");

    document.getElementById("saveButton").addEventListener("click", function() {
        const key = "test_data";
        const value = "12345";

        saveToIndexedDB(key, value, function(error) {
            if (error) {
                messageElement.textContent = "保存エラー: " + error;
            } else {
                messageElement.textContent = "保存しました";
            }
        });
    });

    document.getElementById("loadButton").addEventListener("click", function() {
        const key = "test_data";

        loadFromIndexedDB(key, function(error, data) {
            if (error) {
                messageElement.textContent = "読み込みエラー: " + error;
            } else {
                messageElement.textContent = "読み込みデータ: " + (data || "データなし");
            }
        });
    });
});
