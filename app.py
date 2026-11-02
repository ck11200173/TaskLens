
import time
from datetime import date

import streamlit as st
from supabase import create_client


# ==========================================
# 1. Basic configuration
# ==========================================

st.set_page_config(
    page_title="TaskLens",
    page_icon="🎯",
    layout="wide"
)

CATEGORIES = [
    "計算分析",
    "程式設計",
    "閱讀研究",
    "寫作報告",
    "記憶背誦",
    "其他"
]


# ==========================================
# 2. Supabase client and session
# ==========================================

if "supabase_client" not in st.session_state:
    st.session_state.supabase_client = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

sb = st.session_state.supabase_client

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "focus_started_at" not in st.session_state:
    st.session_state.focus_started_at = None

if "focus_elapsed" not in st.session_state:
    st.session_state.focus_elapsed = 0


# ==========================================
# 3. Authentication
# ==========================================

def login_page():

    st.title("🎯 TaskLens")
    st.caption("智慧學業時序流與風險預警引擎")

    st.divider()

    login_tab, signup_tab = st.tabs([
        "登入 Login",
        "註冊 Sign up"
    ])

    with login_tab:

        st.subheader("歡迎回到 TaskLens")

        with st.form("login_form"):

            email = st.text_input("Email")
            password = st.text_input(
                "密碼",
                type="password"
            )

            submitted = st.form_submit_button(
                "登入",
                use_container_width=True
            )

            if submitted:

                try:
                    result = sb.auth.sign_in_with_password({
                        "email": email.strip(),
                        "password": password
                    })

                    st.session_state.user_id = result.user.id
                    st.session_state.user_email = result.user.email

                    st.success("登入成功！")
                    st.rerun()

                except Exception:
                    st.error("登入失敗，請檢查 Email 和密碼。")

    with signup_tab:

        st.subheader("建立個人帳號")

        with st.form("signup_form"):

            email = st.text_input(
                "Email",
                key="signup_email"
            )

            password = st.text_input(
                "設定密碼",
                type="password",
                key="signup_password"
            )

            confirm_password = st.text_input(
                "確認密碼",
                type="password"
            )

            submitted = st.form_submit_button(
                "建立帳號",
                use_container_width=True
            )

            if submitted:

                if not email.strip():
                    st.error("請輸入 Email。")

                elif len(password) < 8:
                    st.error("密碼至少需要 8 個字元。")

                elif password != confirm_password:
                    st.error("兩次輸入的密碼不一致。")

                else:

                    try:
                        result = sb.auth.sign_up({
                            "email": email.strip(),
                            "password": password
                        })

                        if result.session is not None:

                            st.session_state.user_id = result.user.id
                            st.session_state.user_email = result.user.email

                            st.success("註冊成功！")
                            st.rerun()

                        else:

                            st.success(
                                "帳號建立成功！請先至信箱完成驗證，"
                                "再回到登入頁面登入。"
                            )

                    except Exception:
                        st.error("註冊失敗，請檢查 Email 或稍後再試。")


# ==========================================
# 4. Verify login
# ==========================================

if st.session_state.user_id is not None:

    try:
        verified_user = sb.auth.get_user().user

        st.session_state.user_id = verified_user.id
        st.session_state.user_email = verified_user.email

    except Exception:

        st.session_state.user_id = None
        st.session_state.user_email = None

        st.warning("登入 Session 已失效，請重新登入。")
        st.rerun()


if st.session_state.user_id is None:

    login_page()
    st.stop()


# ==========================================
# 5. User sidebar
# ==========================================

with st.sidebar:

    st.title("🎯 TaskLens")

    st.caption("個人學業管理系統")

    st.write("目前登入帳號：")
    st.write(st.session_state.user_email)

    if st.button("登出", use_container_width=True):

        sb.auth.sign_out()

        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.focus_started_at = None
        st.session_state.focus_elapsed = 0

        st.rerun()


# ==========================================
# 6. Database operations
# ==========================================

def load_tasks():

    result = (
        sb.table("tasks")
        .select("*")
        .eq("user_id", st.session_state.user_id)
        .order("deadline")
        .execute()
    )

    return result.data or []


def insert_task(task):

    # user_id is assigned by the database using auth.uid()
    sb.table("tasks").insert(task).execute()


def update_task(task_id, changes):

    sb.table("tasks").update(changes).eq(
        "id", task_id
    ).eq(
        "user_id", st.session_state.user_id
    ).execute()


def delete_task(task_id):

    sb.table("tasks").delete().eq(
        "id", task_id
    ).eq(
        "user_id", st.session_state.user_id
    ).execute()


# Load the current user's tasks
try:

    st.session_state.tasks = load_tasks()

except Exception as e:

    st.error("無法讀取課業資料，請檢查 Supabase 權限設定。")
    st.stop()


# ==========================================
# 7. Risk engine
# ==========================================

def calculate_risk(task):

    if task["completed"]:
        return 0

    deadline = date.fromisoformat(
        str(task["deadline"])[:10]
    )

    days_left = (deadline - date.today()).days

    if days_left <= 0:
        urgency = 65
    elif days_left == 1:
        urgency = 50
    elif days_left <= 3:
        urgency = 35
    elif days_left <= 7:
        urgency = 20
    else:
        urgency = 5

    workload = min(float(task["hours"]) * 3, 30)

    return min(urgency + workload, 100)


def risk_level(score):

    if score >= 70:
        return "🔴 高風險"

    elif score >= 40:
        return "🟡 中風險"

    return "🟢 低風險"


def get_sorted_tasks():

    tasks = []

    for task in st.session_state.tasks:

        item = task.copy()
        item["risk"] = calculate_risk(item)

        tasks.append(item)

    return sorted(
        tasks,
        key=lambda x: (
            x["completed"],
            -x["risk"],
            x["deadline"]
        )
    )


# ==========================================
# 8. Dashboard
# ==========================================

st.title("🎯 TaskLens")

st.caption("智慧學業時序流與風險預警引擎")

tasks = get_sorted_tasks()

pending = [
    t for t in tasks
    if not t["completed"]
]

completed = [
    t for t in tasks
    if t["completed"]
]

high_risk = [
    t for t in pending
    if t["risk"] >= 70
]

col1, col2, col3, col4 = st.columns(4)

col1.metric("總任務數", len(tasks))
col2.metric("待完成", len(pending))
col3.metric("高風險任務", len(high_risk))

col4.metric(
    "預估剩餘時數",
    f"{sum(float(t['hours']) for t in pending):.1f} h"
)

st.divider()


# ==========================================
# 9. Task creation
# ==========================================

st.subheader("➕ 新增任務")

with st.form("new_task_form"):

    title = st.text_input("任務名稱")

    c1, c2, c3 = st.columns(3)

    deadline = c1.date_input(
        "截止日期",
        value=date.today()
    )

    hours = c2.number_input(
        "預估所需時數",
        min_value=0.5,
        max_value=500.0,
        value=2.0,
        step=0.5
    )

    category = c3.selectbox(
        "認知類型",
        CATEGORIES
    )

    submitted = st.form_submit_button(
        "新增任務",
        use_container_width=True
    )

    if submitted:

        if not title.strip():

            st.error("請輸入任務名稱。")

        else:

            new_task = {
                "title": title.strip(),
                "deadline": deadline.isoformat(),
                "hours": hours,
                "category": category,
                "completed": False
            }

            try:

                insert_task(new_task)

                st.success("任務新增成功！")
                st.rerun()

            except Exception as e:

                st.error(f"新增失敗：{e}")


st.divider()


# ==========================================
# 10. Smart task ranking
# ==========================================

st.subheader("📊 智慧任務排序")

if not tasks:

    st.info("目前沒有任務，請先新增任務。")

else:

    for task in tasks:

        with st.container(border=True):

            c1, c2, c3 = st.columns([5, 2, 2])

            status = (
                "✅ 已完成"
                if task["completed"]
                else "⏳ 待完成"
            )

            c1.markdown(f"**{task['title']}**")

            c1.caption(
                f"{task['category']} ｜ {status}"
            )

            c2.write(f"截止：{task['deadline']}")

            c2.write(
                f"預估：{task['hours']} 小時"
            )

            c3.metric(
                "風險指數",
                f"{task['risk']}/100",
                delta=risk_level(task["risk"]),
                delta_color="off"
            )


st.divider()


# ==========================================
# 11. Task management
# ==========================================

st.subheader("🛠️ 任務管理")

if tasks:

    task_map = {
        t["id"]: t for t in tasks
    }

    selected_id = st.selectbox(
        "選擇要管理的任務",
        options=list(task_map.keys()),
        format_func=lambda x: task_map[x]["title"]
    )

    selected_task = task_map[selected_id]

    c1, c2 = st.columns(2)

    with c1:

        if selected_task["completed"]:

            if st.button("重新開啟任務"):

                try:

                    update_task(
                        selected_id,
                        {"completed": False}
                    )

                    st.rerun()

                except Exception as e:

                    st.error(f"修改失敗：{e}")

        else:

            if st.button("標記為已完成"):

                try:

                    update_task(
                        selected_id,
                        {"completed": True}
                    )

                    st.rerun()

                except Exception as e:

                    st.error(f"修改失敗：{e}")

    with c2:

        if st.button("刪除任務"):

            try:

                delete_task(selected_id)
                st.rerun()

            except Exception as e:

                st.error(f"刪除失敗：{e}")

    with st.expander("編輯任務"):

        with st.form("edit_task_form"):

            new_title = st.text_input(
                "任務名稱",
                value=selected_task["title"]
            )

            new_deadline = st.date_input(
                "截止日期",
                value=date.fromisoformat(
                    str(selected_task["deadline"])[:10]
                ),
                key="edit_deadline"
            )

            new_hours = st.number_input(
                "預估時數",
                min_value=0.5,
                max_value=500.0,
                value=float(selected_task["hours"]),
                step=0.5,
                key="edit_hours"
            )

            category_index = (
                CATEGORIES.index(selected_task["category"])
                if selected_task["category"] in CATEGORIES
                else len(CATEGORIES) - 1
            )

            new_category = st.selectbox(
                "認知類型",
                CATEGORIES,
                index=category_index,
                key="edit_category"
            )

            if st.form_submit_button("儲存修改"):

                if not new_title.strip():

                    st.error("任務名稱不能為空。")

                else:

                    try:

                        update_task(
                            selected_id,
                            {
                                "title": new_title.strip(),
                                "deadline": new_deadline.isoformat(),
                                "hours": new_hours,
                                "category": new_category
                            }
                        )

                        st.success("修改成功！")
                        st.rerun()

                    except Exception as e:

                        st.error(f"修改失敗：{e}")

else:

    st.info("目前沒有可管理的任務。")


st.divider()


# ==========================================
# 12. Cognitive classification
# ==========================================

st.subheader("🧠 認知類型分類")

groups = {}

for task in pending:

    groups.setdefault(
        task["category"], []
    ).append(task)

if groups:

    for category, group in groups.items():

        with st.expander(
            f"{category} ({len(group)} 項任務)"
        ):

            for task in group:

                st.write(
                    f"- {task['title']} "
                    f"｜ {task['hours']} 小時"
                )

else:

    st.info("目前沒有待完成任務。")


st.divider()


# ==========================================
# 13. Focus mode
# ==========================================

st.subheader("⏱️ 專注模式")

if pending:

    focus_map = {
        t["id"]: t for t in pending
    }

    focus_id = st.selectbox(
        "選擇專注任務",
        options=list(focus_map.keys()),
        format_func=lambda x: focus_map[x]["title"],
        key="focus_task",
        disabled=st.session_state.focus_started_at is not None
    )

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "▶ 開始專注",
            use_container_width=True,
            disabled=st.session_state.focus_started_at is not None
        ):

            st.session_state.focus_task_id = focus_id
            st.session_state.focus_started_at = time.time()

            st.rerun()

    with c2:

        if st.button(
            "⏹ 結束專注",
            use_container_width=True,
            disabled=st.session_state.focus_started_at is None
        ):

            elapsed = (
                time.time()
                - st.session_state.focus_started_at
            )

            st.session_state.focus_elapsed += int(elapsed)
            st.session_state.focus_started_at = None

            st.rerun()

    if st.session_state.focus_started_at is not None:

        current_focus = focus_map.get(
            st.session_state.get("focus_task_id")
        )

        if current_focus:
            st.caption(
                f"目前專注：{current_focus['title']}"
            )

    @st.fragment(run_every="1s")
    def focus_clock():

        elapsed = st.session_state.focus_elapsed

        if st.session_state.focus_started_at is not None:

            elapsed += int(
                time.time()
                - st.session_state.focus_started_at
            )

        minutes, seconds = divmod(elapsed, 60)

        hours_display, minutes = divmod(minutes, 60)

        st.metric(
            "累積專注時間",
            f"{hours_display:02d}:{minutes:02d}:{seconds:02d}"
        )

    focus_clock()

else:

    st.info("請先新增一項未完成任務。")


# ==========================================
# 14. Footer
# ==========================================

st.divider()

st.caption(
    "TaskLens MVP v2 | Personal Academic Task Management System"
)
