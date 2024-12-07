
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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

# ヘルパー関数：30分間隔の時刻リストを作成
def get_time_options():
    from datetime import time as dt_time  # 明示的に datetime.time を dt_time に変更
    return [dt_time(hour, minute).strftime("%H:%M") for hour in range(24) for minute in (0, 30)]

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
if st.button("服薬を追加"):
    health_data["服薬"].append({"種類": new_medicine, "時刻": new_time})

st.write(pd.DataFrame(health_data["服薬"]))

# 運動記録 (横配置)
st.write("#### 運動記録")
col1, col2 = st.columns(2)
new_exercise = col1.text_input("運動種類", key="new_exercise")
new_exercise_time = col2.selectbox("運動時刻", time_options, key="new_exercise_time")
if st.button("運動を追加"):
    health_data["運動"].append({"種類": new_exercise, "時刻": new_exercise_time})

st.write(pd.DataFrame(health_data["運動"]))

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

# 簡易カレンダー
st.write("### 簡易カレンダー: ジャンルのみ")
simple_calendar = pd.DataFrame(
    {date: st.session_state["data"][date]["ジャンル"] for date in selected_dates},
    index=[f"{hour}:00" for hour in range(24)]
)
st.dataframe(simple_calendar.style.applymap(lambda v: f"background-color: {genre_colors.get(v, '#FFFFFF')};"))

# 詳細カレンダー
st.write(f"### 詳細カレンダー: {selected_dates[0]} 〜 {selected_dates[-1]}")
detailed_calendar_data = []

for date in selected_dates:
    day_data = st.session_state["data"][date]
    day_data = day_data.rename(
        columns={
            "行動": f"{date} 行動",
            "理由": f"{date} 理由",
            "結果": f"{date} 結果"
        }
    )
    detailed_calendar_data.append(day_data[[
        f"{date} 行動", f"{date} 理由", f"{date} 結果"
    ]])

# データ結合
detailed_calendar = pd.concat(detailed_calendar_data, axis=1)

# 表示
st.dataframe(detailed_calendar)

# 統一健康カレンダー
st.write("### 健康カレンダー")
health_calendar = pd.DataFrame(columns=dates_range, index=[
    "朝食", "昼食", "夕食", "間食", "服薬", "運動", 
    "体調(肉体)", "体調(精神)", "体調(頭脳)"
])

for date in dates_range:
    if date in st.session_state["health"]:
        health_entry = st.session_state["health"][date]
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

st.dataframe(health_calendar)

import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pandas as pd
import streamlit as st

# Google Drive API 認証
def authenticate_google_drive():
    service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_KEY"])
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

# Google Drive にファイルをアップロード
def upload_to_google_drive(file_name, file_path):
    service = authenticate_google_drive()

    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype='text/csv')

    try:
        # ファイルのアップロード
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = uploaded_file.get('id')
        print(f"Uploaded {file_name} to Google Drive. File ID: {file_id}")

        # 自分のGoogleアカウントに自動共有
        user_email = "k.iwahori.eps@gmail.com"  # 共有したいGoogleアカウントのメールアドレス
        share_file_with_user(file_id, user_email)

        return file_id
    except Exception as e:
        print(f"Failed to upload {file_name}: {e}")
        raise

# Google Drive ファイルを共有
def share_file_with_user(file_id, user_email):
    service = authenticate_google_drive()

    permission = {
        'type': 'user',  # ユーザーに共有
        'role': 'writer',  # 必要に応じて 'reader' に変更
        'emailAddress': user_email  # 引数として受け取るメールアドレス
    }

    try:
        service.permissions().create(
            fileId=file_id,
            body=permission,
            fields='id'
        ).execute()
        print(f"File shared with {user_email}")
    except Exception as e:
        print(f"Failed to share file: {e}")
        raise

# サンプルファイルを保存してアップロード
def save_calendars_to_drive():
    # ローカルに保存
    simple_file_path = "simple_calendar.csv"
    detailed_file_path = "detailed_calendar.csv"
    health_file_path = "health_calendar.csv"
    
    # CSVファイルを保存する（例として）
    pd.DataFrame({"Sample": [1, 2, 3]}).to_csv(simple_file_path, index=False)
    pd.DataFrame({"Sample": [4, 5, 6]}).to_csv(detailed_file_path, index=False)
    pd.DataFrame({"Sample": [7, 8, 9]}).to_csv(health_file_path, index=False)

    # Google Drive にアップロード
    upload_to_google_drive("simple_calendar.csv", simple_file_path)
    upload_to_google_drive("detailed_calendar.csv", detailed_file_path)
    upload_to_google_drive("health_calendar.csv", health_file_path)

# ボタンで保存をトリガー
if st.button("Google Drive にカレンダー形式で保存"):
    try:
        save_calendars_to_drive()
        st.success("3つのカレンダーをGoogle Driveに保存しました！")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
