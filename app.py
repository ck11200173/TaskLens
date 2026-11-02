import json
import time
import uuid
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st


# ==========================================
# 1. Basic configuration
# ==========================================

st.set_page_config(
    page_title="TaskLens",
    page_icon="🎯",
    layout="wide"
)

DATA_FILE = Path(__file__).parent / "tasks.json"

CATEGORIES = [
    "計算分析",
    "程式設計",
    "閱讀研究",
    "寫作報告",
    "記憶背誦",
    "其他"
]


# ==========================================
# 2. Data management
# ==========================================

def load_tasks():
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_tasks():
    DATA_FILE.write_text(
        json.dumps(
            st.session_state.tasks,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )


if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()

if "focus_started_at" not in st.session_state:
    st.session_state.focus_started_at = None

if "focus_elapsed" not in st.session_state:
    st.session_state.focus_elapsed = 0


# ==========================================
# 3. Risk engine
# ==========================================

def calculate_risk(task):
    if task["completed"]:
        return 0

    deadline = date.fromisoformat(task["deadline"])
    days_left = (deadline - date.today()).days

    # Deadline urgency
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

    # Estimated workload
    workload = min(task["hours"] * 3, 30)

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
# 4. Dashboard
# ==========================================

st.title("🎯 TaskLens")
st.caption("智慧學業時序流與風險預警引擎")

tasks = get_sorted_tasks()

pending = [t for t in tasks if not t["completed"]]
completed = [t for t in tasks if t["completed"]]
high_risk = [t for t in pending if t["risk"] >= 70]

col1, col2, col3, col4 = st.columns(4)

col1.metric("總任務數", len(tasks))
col2.metric("待完成", len(pending))
col3.metric("高風險任務", len(high_risk))
col4.metric(
    "預估剩餘時數",
    f"{sum(t['hours'] for t in pending):.1f} h"
)

st.divider()


# ==========================================
# 5. Task creation
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
                "id": str(uuid.uuid4()),
                "title": title.strip(),
                "deadline": deadline.isoformat(),
                "hours": hours,
                "category": category,
                "completed": False
            }

            st.session_state.tasks.append(new_task)
            save_tasks()

            st.success("任務新增成功！")
            st.rerun()


st.divider()


# ==========================================
# 6. Smart task ranking
# ==========================================

st.subheader("📊 智慧任務排序")

if not tasks:
    st.info("目前沒有任務，請先新增任務。")
else:
    for task in tasks:
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 2, 2])

            status = "✅ 已完成" if task["completed"] else "⏳ 待完成"

            c1.markdown(f"**{task['title']}**")
            c1.caption(
                f"{task['category']} ｜ {status}"
            )

            c2.write(
                f"截止：{task['deadline']}"
            )
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
# 7. Task management
# ==========================================

st.subheader("🛠️ 任務管理")

if tasks:
    task_map = {
        t["id"]: t for t in st.session_state.tasks
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
                selected_task["completed"] = False
                save_tasks()
                st.rerun()
        else:
            if st.button("標記為已完成"):
                selected_task["completed"] = True
                save_tasks()
                st.rerun()

    with c2:
        if st.button("刪除任務"):
            st.session_state.tasks = [
                t for t in st.session_state.tasks
                if t["id"] != selected_id
            ]
            save_tasks()
            st.rerun()

    with st.expander("編輯任務"):
        with st.form("edit_task_form"):
            new_title = st.text_input(
                "任務名稱",
                value=selected_task["title"]
            )

            new_deadline = st.date_input(
                "截止日期",
                value=date.fromisoformat(
                    selected_task["deadline"]
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

            new_category = st.selectbox(
                "認知類型",
                CATEGORIES,
                index=CATEGORIES.index(
                    selected_task["category"]
                ),
                key="edit_category"
            )

            if st.form_submit_button("儲存修改"):
                if new_title.strip():
                    selected_task.update({
                        "title": new_title.strip(),
                        "deadline": new_deadline.isoformat(),
                        "hours": new_hours,
                        "category": new_category
                    })
                    save_tasks()
                    st.success("修改成功！")
                    st.rerun()
                else:
                    st.error("任務名稱不能為空。")


st.divider()


# ==========================================
# 8. Cognitive classification
# ==========================================

st.subheader("🧠 認知類型分類")

groups = {}

for task in pending:
    groups.setdefault(task["category"], []).append(task)

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
# 9. Focus mode
# ==========================================

st.subheader("⏱️ 專注模式")

focus_tasks = [
    t for t in pending
]

if focus_tasks:
    focus_map = {
        t["id"]: t for t in focus_tasks
    }

    focus_id = st.selectbox(
        "選擇專注任務",
        options=list(focus_map.keys()),
        format_func=lambda x: focus_map[x]["title"],
        key="focus_task"
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "▶ 開始專注",
            use_container_width=True
        ):
            st.session_state.focus_started_at = time.time()
            st.rerun()

    with c2:
        if st.button(
            "⏹ 結束專注",
            use_container_width=True
        ):
            if st.session_state.focus_started_at is not None:
                elapsed = (
                    time.time()
                    - st.session_state.focus_started_at
                )
                st.session_state.focus_elapsed += int(elapsed)
                st.session_state.focus_started_at = None
            st.rerun()

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
# 10. Footer
# ==========================================

st.divider()

st.caption(
    "TaskLens MVP v1 | Academic Task Management System"
)