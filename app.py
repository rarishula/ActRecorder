
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from googleapiclient.http import MediaIoBaseDownload
import copy
from pathlib import Path
import mimetypes
import streamlit.components.v1 as components

# ヘルパー関数：30分間隔の時刻リストを作成
def get_time_options():
    from datetime import time as dt_time  # 明示的に datetime.time を dt_time に変更
    return [dt_time(hour, minute).strftime("%H:%M") for hour in range(24) for minute in (0, 30)]

def generate_simple_calendar(selected_dates, data_session):
    return pd.DataFrame(
        {date: data_session[date]["ジャンル"] for date in selected_dates},
        index=[f"{hour}:00" for hour in range(24)]
    )

def generate_detailed_calendar(selected_dates, data_session):
    detailed_calendar_data = []
    for date in selected_dates:
        day_data = data_session[date]
        day_data = day_data.rename(
            columns={
                "行動": f"{date} 行動",
                "理由": f"{date} 理由",
                "結果": f"{date} 結果"
            }
        )
        detailed_calendar_data.append(day_data[[f"{date} 行動", f"{date} 理由", f"{date} 結果"]])
    return pd.concat(detailed_calendar_data, axis=1)

def generate_health_calendar(dates_range, health_session):
    health_calendar = pd.DataFrame(columns=dates_range, index=[
        "朝食", "昼食", "夕食", "間食", "服薬", "運動",
        "体調(肉体)", "体調(精神)", "体調(頭脳)"
    ])
    for date in dates_range:
        if date in health_session:
            health_entry = health_session[date]
            health_calendar.loc["朝食", date] = health_entry["食事"]["朝食"]
            health_calendar.loc["昼食", date] = health_entry["食事"]["昼食"]
            health_calendar.loc["夕食", date] = health_entry["食事"]["夕食"]
            health_calendar.loc["間食", date] = health_entry["食事"]["間食"]
            health_calendar.loc["服薬", date] = "\n".join(
                [f"{entry['種類']} ({entry['時刻']})" for entry in health_entry["服薬"]]
            )
            health_calendar.loc["運動", date] = "\n".join(
                [f"{entry['種類']} ({entry['時刻']})" for entry in health_entry["運動"]]
            )
            health_calendar.loc["体調(肉体)", date] = health_entry["体調"]["肉体"]
            health_calendar.loc["体調(精神)", date] = health_entry["体調"]["精神"]
            health_calendar.loc["体調(頭脳)", date] = health_entry["体調"]["頭脳"]
    return health_calendar

# Google Drive API 認証
def authenticate_google_drive():
    service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_KEY"])
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)


# Google Drive から CSV を pandas の DataFrame としてダウンロードする
def download_csv_as_dataframe(service, file_id):
    """
    Google Drive から CSV ファイルをダウンロードして pandas のデータフレームとして返す関数。
    """
    request = service.files().get_media(fileId=file_id)
    file_data = io.BytesIO()
    downloader = MediaIoBaseDownload(file_data, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    file_data.seek(0)
    return pd.read_csv(file_data)

def get_latest_files(service, prefixes):
    """
    Google Drive 上で指定された複数の prefix にマッチする最新ファイルを検索する。

    Args:
        service: Google Drive API サービスオブジェクト。
        prefixes: プレフィックスのリスト (例: ["health_calendar", "detailed_calendar", "simple_calendar"]).

    Returns:
        dict: 各プレフィックスに対応する最新ファイル情報の辞書。
              (例: {"health_calendar": {"id": "file_id", "name": "health_calendar_2024-12-08.csv"}, ...})
    """
    query = " or ".join([f"name contains '{prefix}'" for prefix in prefixes])
    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc"
    ).execute()

    all_files = results.get("files", [])
    if not all_files:
        raise FileNotFoundError(f"Google Drive 内に指定されたプレフィックスを含むファイルが見つかりません。")

    latest_files = {}
    for prefix in prefixes:
        for file in all_files:
            if prefix in file["name"]:
                latest_files[prefix] = file
                break  # 各プレフィックスごとに最初の一致を取得

    return latest_files



def load_data_from_drive():
    try:
        service = authenticate_google_drive()

        # 一括でファイルを取得
        prefixes = ["health_calendar", "detailed_calendar", "simple_calendar"]
        latest_files = get_latest_files(service, prefixes)

        # 各ファイルをダウンロード
        health_df = download_csv_as_dataframe(service, latest_files["health_calendar"]["id"])
        detailed_df = download_csv_as_dataframe(service, latest_files["detailed_calendar"]["id"])
        simple_df = download_csv_as_dataframe(service, latest_files["simple_calendar"]["id"])

        # session_state に反映
        st.session_state["health_data"] = health_df
        st.session_state["detailed_data"] = detailed_df
        st.session_state["simple_data"] = simple_df

        st.success("Google Drive からデータを効率的に読み込みました！")
    except Exception as e:
        st.error(f"データの読み込み中にエラーが発生しました: {e}")


# Google Drive でファイルをアップロード
def upload_to_google_drive(file_name, file_path):
    service = authenticate_google_drive()

    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype='text/csv')

    try:
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = uploaded_file.get('id')
        st.session_state["uploaded_file_ids"][file_name] = file_id  # ファイルIDを保存
        print(f"Uploaded {file_name} to Google Drive. File ID: {file_id}")

        return file_id
    except Exception as e:
        print(f"Failed to upload {file_name}: {e}")
        raise

# 手動でファイルを共有する関数
def share_file_with_user(file_id, user_email):
    service = authenticate_google_drive()

    permission = {
        'type': 'user',  # ユーザー共有
        'role': 'writer',  # 書き込み可能
        'emailAddress': user_email  # 共有するメールアドレス
    }

    try:
        service.permissions().create(
            fileId=file_id,
            body=permission,
            fields='id'
        ).execute()
        print(f"Shared file with {user_email}")
    except Exception as e:
        print(f"Failed to share file: {e}")
        raise

def save_calendars_to_drive():
    # 現在の日付を取得
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # ファイル名に日付を追加
    simple_file_path = f"simple_calendar_{current_date}.csv"
    detailed_file_path = f"detailed_calendar_{current_date}.csv"
    health_file_path = f"health_calendar_{current_date}.csv"

    # ローカルに保存
    simple_calendar.to_csv(simple_file_path, index=True)
    detailed_calendar.to_csv(detailed_file_path, index=True)
    health_calendar.to_csv(health_file_path, index=True)

    # Google Drive にアップロード
    upload_to_google_drive(f"simple_calendar_{current_date}.csv", simple_file_path)
    upload_to_google_drive(f"detailed_calendar_{current_date}.csv", detailed_file_path)
    upload_to_google_drive(f"health_calendar_{current_date}.csv", health_file_path)

def has_changes():
    """監視対象のデータが変更されたかを判定"""
    # データフレームを文字列に変換して比較
    current_data_str = {k: v.to_csv() for k, v in st.session_state["data"].items()}
    last_saved_data_str = {k: v.to_csv() for k, v in st.session_state["last_saved_state"]["data"].items()}

    current_health_str = {k: str(v) for k, v in st.session_state["health"].items()}
    last_saved_health_str = {k: str(v) for k, v in st.session_state["last_saved_state"]["health"].items()}

    return current_data_str != last_saved_data_str or current_health_str != last_saved_health_str

def update_last_saved_state():
    """最後に保存された状態を更新"""
    st.session_state["last_saved_state"] = {
        "data": {k: v.copy() for k, v in st.session_state["data"].items()},
        "health": copy.deepcopy(st.session_state["health"]),
    }


def save_if_needed():
    """変更があれば保存を実行"""
    if has_changes():
        save_calendars_to_drive()  # 保存処理
        update_last_saved_state()  # スナップショットを更新
        st.success("変更を検知し、自動保存しました！")
    else:
        st.write("変更は検出されませんでした。")

import streamlit as st
import streamlit.components.v1 as components
import json

# JavaScriptから受信したデータをセッションに反映
def update_session(data):
    try:
        # JSONを辞書形式に変換してセッションステートに保存
        st.session_state["data"] = data.get("data", {})
        st.session_state["health"] = data.get("health", {})
        print("セッションデータが正常に復元されました！")  # 成功メッセージをコンソールに出力
    except Exception as e:
        print(f"データの復元中にエラーが発生しました: {e}")  # エラーメッセージをコンソールに出力

# 自動実行するHTML + JavaScriptの埋め込み
auto_load_html = """
<script>
    function loadFromLocalStorage() {
        const storedData = localStorage.getItem('sessionData');
        if (storedData) {
            const parsedData = JSON.parse(storedData);

            // Streamlitにデータを送信
            const streamlitData = JSON.stringify(parsedData);
            Streamlit.setComponentValue(streamlitData); // Streamlitにデータを送信
            console.log("データをローカルストレージから読み込み、Streamlitに送信しました。");
        } else {
            console.log("保存されたデータがありません");
        }
    }

    function waitForStreamlit() {
        if (typeof Streamlit !== "undefined") {
            // Streamlitが利用可能になったら実行
            loadFromLocalStorage();
        } else {
            // Streamlitが未定義の場合、100ms後に再試行
            setTimeout(waitForStreamlit, 100);
        }
    }

    // 初期化
    waitForStreamlit();
</script>
"""

# HTMLコンポーネントから受信したデータを確認し、セッションステートに反映
data_from_js = components.html(auto_load_html, height=0)

if data_from_js:
    try:
        st.write(f"JavaScriptから受信したデータ: {data_from_js}")  # 受信データを確認
        parsed_data = json.loads(data_from_js)  # JSON文字列を辞書形式に変換
        update_session(parsed_data)  # セッションステートに反映
    except json.JSONDecodeError:
        st.write("受信したデータが正しいJSON形式ではありません")  # デバッグ用
    except Exception as e:
        st.write(f"データ更新中にエラーが発生しました: {e}")
else:
    st.write("JavaScriptからのデータを受信できませんでした")




# ジャンルと色の定義（簡易カレンダー用）
genres = [
    "仕事", "勉強", "ゲーム(練習)", "ソシャゲ", "ゲーム(その他)",
    "SNS・匿名掲示板", "遊び", "性", "食事", "睡眠", "マルチタスク", "その他"
]
genre_colors = {
    "仕事": "#FFFFCC", "勉強": "#CCFFFF", "ゲーム(練習)": "#FFD700",
    "ソシャゲ": "#FFB6C1", "ゲーム(その他)": "#ADD8E6",
    "SNS・匿名掲示板": "#D3D3D3", "遊び": "#98FB98", "性": "#FFC0CB",
    "食事": "#FFA500", "睡眠": "#4682B4", "マルチタスク": "#9370DB", "その他": "#E0E0E0"
}

# 初期化
st.title("ジャンル分け記録アプリ")
dates_range = pd.date_range("2024-12-01", "2024-12-31").strftime("%Y-%m-%d").tolist()

# 現在の日付とその週の月曜日を取得
today = datetime.now()
monday_of_week = today - timedelta(days=today.weekday())
start_date = monday_of_week.strftime("%Y-%m-%d")

# 表示する1週間分の日付
start_index = dates_range.index(start_date)
end_index = min(start_index + 7, len(dates_range))  # 最大7日間
selected_dates = dates_range[start_index:end_index]

# サンプルデータ管理
if "data" not in st.session_state:
    st.session_state["data"] = {}

for date in dates_range:
    if date not in st.session_state["data"]:
        st.session_state["data"][date] = pd.DataFrame(
            index=[f"{hour}:00" for hour in range(24)],
            columns=["ジャンル", "行動", "理由", "結果"]
        )

# 入力フォームのための選択日付
selected_date = st.date_input("記録する日付を選んでください", value=datetime.now())
selected_date_str = selected_date.strftime("%Y-%m-%d")

# 入力フォーム
st.write(f"### {selected_date_str} の記録")
data = st.session_state["data"][selected_date_str]

for time in data.index:
    st.write(f"#### {time}")
    col1, col2, col3, col4 = st.columns(4)
    genre = col1.selectbox("ジャンル", genres, key=f"{selected_date_str}_ジャンル_{time}")
    action = col2.text_input("行動", key=f"{selected_date_str}_行動_{time}")
    reason = col3.text_input("理由", key=f"{selected_date_str}_理由_{time}")
    result = col4.text_input("結果", key=f"{selected_date_str}_結果_{time}")

    # データに反映
    data.loc[time, "ジャンル"] = genre
    data.loc[time, "行動"] = action
    data.loc[time, "理由"] = reason
    data.loc[time, "結果"] = result



# セッション状態の初期化
if "health" not in st.session_state:
    st.session_state["health"] = {}



# 健康データ初期化
if selected_date_str not in st.session_state["health"]:
    st.session_state["health"][selected_date_str] = {
        "食事": {"朝食": "しなかった", "昼食": "しなかった", "夕食": "しなかった", "間食": "しなかった"},
        "服薬": [],
        "運動": [],
        "体調": {"肉体": "", "精神": "", "頭脳": ""}
    }

# 健康データ取得
health_data = st.session_state["health"][selected_date_str]

# 健康記録フォーム
st.write(f"### {selected_date_str} の健康記録")

# 食事記録 (横配置)
st.write("#### 食事記録")
time_options = ["しなかった"] + get_time_options()

col1, col2, col3, col4 = st.columns(4)
health_data["食事"]["朝食"] = col1.selectbox("朝食", time_options, key="朝食")
health_data["食事"]["昼食"] = col2.selectbox("昼食", time_options, key="昼食")
health_data["食事"]["夕食"] = col3.selectbox("夕食", time_options, key="夕食")
health_data["食事"]["間食"] = col4.selectbox("間食", time_options, key="間食")

# 服薬記録 (横配置)
st.write("#### 服薬記録")
col1, col2 = st.columns(2)
new_medicine = col1.text_input("服薬種類", key="new_medicine")
new_time = col2.selectbox("服薬時刻", time_options, key="new_medicine_time")


# 運動記録 (横配置)
st.write("#### 運動記録")
col1, col2 = st.columns(2)
new_exercise = col1.text_input("運動種類", key="new_exercise")
new_exercise_time = col2.selectbox("運動時刻", time_options, key="new_exercise_time")


# 体調記録 (横配置)
st.write("#### 体調記録")
col1, col2, col3 = st.columns(3)
health_data["体調"]["肉体"] = col1.text_input(
    "肉体の状態", value=health_data["体調"]["肉体"], key="condition_body"
)
health_data["体調"]["精神"] = col2.text_input(
    "精神の状態", value=health_data["体調"]["精神"], key="condition_mind"
)
health_data["体調"]["頭脳"] = col3.text_input(
    "頭脳の状態", value=health_data["体調"]["頭脳"], key="condition_brain"
)


# カレンダー生成
simple_calendar = generate_simple_calendar(selected_dates, st.session_state["data"])
detailed_calendar = generate_detailed_calendar(selected_dates, st.session_state["data"])
health_calendar = generate_health_calendar(dates_range, st.session_state["health"])

# 常時表示
st.write("### 簡易カレンダー: ジャンルのみ")
st.dataframe(simple_calendar.style.applymap(lambda v: f"background-color: {genre_colors.get(v, '#FFFFFF')};"))

st.write(f"### 詳細カレンダー: {selected_dates[0]} 〜 {selected_dates[-1]}")
st.dataframe(detailed_calendar)

st.write("### 健康カレンダー")
st.dataframe(health_calendar)

# 初回のみデータをロード
if "data_loaded" not in st.session_state:
    load_data_from_drive()
    st.session_state["data_loaded"] = True

# 表示
st.write("### 健康カレンダー")
st.dataframe(st.session_state.get("health_data", pd.DataFrame()))

st.write("### 詳細カレンダー")
st.dataframe(st.session_state.get("detailed_data", pd.DataFrame()))

st.write("### 簡易カレンダー")
st.dataframe(st.session_state.get("simple_data", pd.DataFrame()))


# ファイルIDを保存するセッション状態の初期化
if "uploaded_file_ids" not in st.session_state:
    st.session_state["uploaded_file_ids"] = {}



# 保存と共有のトリガーを分離
if st.button("Google Drive に保存"):
    try:
        save_calendars_to_drive()  # 保存関数を実行
        st.success("3つのカレンダーをGoogle Driveに保存しました！")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

if st.button("Google Drive で共有"):
    try:
        user_email = "k.iwahori.eps@gmail.com"
        for file_name, file_id in st.session_state["uploaded_file_ids"].items():
            share_file_with_user(file_id, user_email)
        st.success(f"Google Drive 上のファイルを {user_email} に共有しました！")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")




# 初期化: 最後に保存された状態を記録
if "last_saved_state" not in st.session_state:
    st.session_state["last_saved_state"] = {
        "data": copy.deepcopy(st.session_state["data"]),
        "health": copy.deepcopy(st.session_state["health"]),
    }


# 保存を10秒ごとにチェック
#save_if_needed()
#count = st_autorefresh(interval=10 * 1000, key="refresh")

import json
import pandas as pd
import streamlit.components.v1 as components

# JSONシリアライズ可能な形式に変換する関数
def make_serializable(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")  # DataFrameを辞書形式に変換
    elif isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}  # 再帰処理
    else:
        return obj  # そのまま利用

# st.session_state["data"]と["health"]を変換
serializable_data = make_serializable(st.session_state.get("data", {}))
serializable_health = make_serializable(st.session_state.get("health", {}))

# 保存ボタンのHTMLを生成
save_button_html = f"""
<script>
    function saveToLocalStorage() {{
        const sessionData = {{
            data: {json.dumps(serializable_data)},
            health: {json.dumps(serializable_health)}
        }};
        localStorage.setItem('sessionData', JSON.stringify(sessionData));
        document.getElementById('status').innerText = 'データをローカルストレージに保存しました！';
    }}
</script>

<div>
    <button onclick="saveToLocalStorage()">ローカルストレージに保存</button>
    <div id="status"></div>
</div>
"""

# HTMLを埋め込み
components.html(save_button_html, height=100)


load_button_html = """
<script>
    function loadFromLocalStorage() {
        const storedData = JSON.parse(localStorage.getItem('sessionData'));
        if (storedData) {
            const { data, health } = storedData;  // dataとhealthを取得
            document.getElementById('status').innerText = `読み込んだデータ: data=${JSON.stringify(data)}, health=${JSON.stringify(health)}`;
        } else {
            document.getElementById('status').innerText = '保存されたデータがありません！';
        }
    }
</script>

<div>
    <button onclick="loadFromLocalStorage()">ローカルストレージから読み込み</button>
    <div id="status"></div>
</div>
"""

components.html(load_button_html, height=100)

import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# JSONから元の形式に復元する関数
def restore_from_serializable(obj):
    if isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
        try:
            return pd.DataFrame(obj)
        except Exception:
            return obj
    elif isinstance(obj, dict):
        return {key: restore_from_serializable(value) for key, value in obj.items()}
    else:
        return obj



# HTML + JavaScriptでローカルストレージから直接復元するボタン
load_to_session_html = """
<script>
    function loadFromLocalStorage() {
        const storedData = localStorage.getItem('sessionData');
        if (storedData) {
            const parsedData = JSON.parse(storedData);
            const data = parsedData.data;
            const health = parsedData.health;

            // Streamlitにデータを送信
            fetch("/streamlit/sessionData", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ data, health })
            }).then(() => {
                document.getElementById('status').innerText = 'データをセッションに復元しました！';
                location.reload(); // ページをリロードして反映
            }).catch(err => {
                console.error('送信エラー:', err);
                document.getElementById('status').innerText = '復元に失敗しました！';
            });
        } else {
            document.getElementById('status').innerText = '保存されたデータがありません！';
        }
    }
</script>

<div>
    <button onclick="loadFromLocalStorage()">ローカルストレージから復元</button>
    <div id="status"></div>
</div>
"""

components.html(load_to_session_html, height=100)

# サーバーサイドでデータを受信
if st.experimental_get_query_params().get("sessionData"):
    try:
        # JSONデータを辞書に変換
        loaded_data = json.loads(st.experimental_get_query_params()["sessionData"][0])

        # 各セクションを復元
        # "data"と"health"をDataFrame形式に変換
        st.session_state["data"] = pd.DataFrame(restore_from_serializable(loaded_data["data"]))
        st.session_state["health"] = pd.DataFrame(restore_from_serializable(loaded_data["health"]))

        st.success("データがセッションに復元されました！")
    except Exception as e:
        st.error(f"データ復元中にエラーが発生しました: {e}")

# デバッグ用ボタン
if st.button("セッションデータをデバッグ表示"):
    if "data" in st.session_state:
        st.write("### デバッグ用 - st.session_state['data']")
        st.json(st.session_state["data"])  # JSON形式で内容を表示
        st.write(f"データ型: {type(st.session_state['data'])}")  # データ型を表示

    if "health" in st.session_state:
        st.write("### デバッグ用 - st.session_state['health']")
        st.json(st.session_state["health"])  # JSON形式で内容を表示
        st.write(f"データ型: {type(st.session_state['health'])}")  # データ型を表示

    if "data" not in st.session_state and "health" not in st.session_state:
        st.warning("セッションにデータがありません。復元を先に行ってください。")



