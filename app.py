import datetime
import pandas as pd
import streamlit as st
from supabase import create_client

from salary_calculations import (
    calculate_basic_daily,
    calculate_basic_salary,
    calculate_night_allowance,
    calculate_regular_overtime,
    calculate_target_bonus,
    calculate_attendance_bonus,
    calculate_31st_day,
    calculate_total_salary,
)


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="WorkPay",
    page_icon="💰",
    layout="wide"
)


# =========================================================
# SUPABASE CONNECTION
# =========================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =========================================================
# SESSION STATE
# =========================================================

if "user" not in st.session_state:
    st.session_state.user = None


# =========================================================
# LOGIN / REGISTER
# =========================================================

if st.session_state.user is None:

    st.title("💰 WorkPay")
    st.write("نظام حساب المرتبات والحضور")

    tab1, tab2 = st.tabs([
        "تسجيل الدخول",
        "إنشاء حساب"
    ])

    # =====================================================
    # LOGIN
    # =====================================================

    with tab1:

        st.subheader("تسجيل الدخول")

        email = st.text_input(
            "البريد الإلكتروني",
            key="login_email"
        )

        password = st.text_input(
            "كلمة المرور",
            type="password",
            key="login_password"
        )

        if st.button(
            "تسجيل الدخول",
            use_container_width=True
        ):

            if not email or not password:

                st.warning(
                    "من فضلك أدخل البريد الإلكتروني وكلمة المرور"
                )

            else:

                try:

                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })

                    st.session_state.user = response.user

                    st.success(
                        "تم تسجيل الدخول بنجاح ✅"
                    )

                    st.rerun()

                except Exception:

                    st.error(
                        "البريد الإلكتروني أو كلمة المرور غير صحيحة"
                    )


    # =====================================================
    # REGISTER
    # =====================================================

    with tab2:

        st.subheader("إنشاء حساب جديد")

        name = st.text_input(
            "الاسم",
            key="register_name"
        )

        register_email = st.text_input(
            "البريد الإلكتروني",
            key="register_email"
        )

        register_password = st.text_input(
            "كلمة المرور",
            type="password",
            key="register_password"
        )

        confirm_password = st.text_input(
            "تأكيد كلمة المرور",
            type="password",
            key="confirm_password"
        )

        if st.button(
            "إنشاء الحساب",
            use_container_width=True
        ):

            if not name or not register_email or not register_password:

                st.warning(
                    "من فضلك املأ جميع البيانات"
                )

            elif register_password != confirm_password:

                st.error(
                    "كلمتا المرور غير متطابقتين"
                )

            elif len(register_password) < 6:

                st.error(
                    "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
                )

            else:

                try:

                    response = supabase.auth.sign_up({
                        "email": register_email,
                        "password": register_password
                    })

                    if response.user:

                        supabase.table("users").insert({
                            "name": name,
                            "email": register_email
                        }).execute()

                        st.success(
                            "تم إنشاء الحساب بنجاح ✅"
                        )

                        st.info(
                            "افتح بريدك الإلكتروني واضغط على رابط التأكيد."
                        )

                except Exception as e:

                    st.error(
                        "حدث خطأ أثناء إنشاء الحساب"
                    )

                    st.exception(e)


# =========================================================
# LOGGED IN
# =========================================================

else:

    user = st.session_state.user


    # =====================================================
    # GET USER DATA
    # =====================================================

    try:

        user_result = (
            supabase
            .table("users")
            .select("*")
            .eq("email", user.email)
            .limit(1)
            .execute()
        )

    except Exception as e:

        st.error(
            "حدث خطأ أثناء قراءة بيانات المستخدم"
        )

        st.exception(e)
        st.stop()


    if not user_result.data:

        st.error(
            "لم يتم العثور على بيانات المستخدم."
        )

        st.stop()


    current_user = user_result.data[0]

    user_id = current_user["id"]


    # =====================================================
    # DATABASE RETENTION: ONLY LATEST TWO SAVED SALARY CYCLES
    # =====================================================
    # لا نحذف البيانات بناءً على تاريخ اليوم.
    # يتم الاحتفاظ دائمًا بأحدث دورتين تم حفظهما فعليًا.

    def keep_latest_two_cycles():
        # نجمع كل دورات المرتب الموجودة للمستخدم من الجدولين معًا.
        all_cycles = set()
        table_rows = {}

        for table_name, month_column, year_column in (
            ("monthly_salary", "month", "year"),
            ("attendance", "salary_month", "salary_year"),
        ):
            rows = (
                supabase
                .table(table_name)
                .select("id, " + month_column + ", " + year_column)
                .eq("user_id", user_id)
                .execute()
            ).data or []

            table_rows[table_name] = (
                rows, month_column, year_column
            )

            for row in rows:
                if (
                    row.get(year_column) is not None
                    and row.get(month_column) is not None
                ):
                    all_cycles.add(
                        (
                            int(row[year_column]),
                            int(row[month_column])
                        )
                    )

        # أحدث دورتين محفوظتين فعليًا، وليس أحدث دورتين حسب تاريخ اليوم.
        latest_two = set(
            sorted(all_cycles, reverse=True)[:2]
        )

        # حذف أي بيانات أقدم من أحدث دورتين من الجدولين.
        for table_name, (rows, month_column, year_column) in table_rows.items():
            for row in rows:
                row_cycle = (
                    int(row[year_column]),
                    int(row[month_column])
                )

                if row_cycle not in latest_two:
                    (
                        supabase
                        .table(table_name)
                        .delete()
                        .eq("id", row["id"])
                        .execute()
                    )

    # =====================================================
    # HEADER
    # =====================================================

    col1, col2 = st.columns([5, 1])

    with col1:

        st.title("💰 WorkPay")

        st.write(
            f"أهلاً بك، {current_user['name']} 👋"
        )


    with col2:

        if st.button(
            "تسجيل الخروج",
            use_container_width=True
        ):

            supabase.auth.sign_out()

            st.session_state.user = None

            st.rerun()


    st.divider()


    # =====================================================
    # CURRENT SALARY CYCLE
    # =====================================================

    today = datetime.date.today()


    month_names = [
        "يناير",
        "فبراير",
        "مارس",
        "أبريل",
        "مايو",
        "يونيو",
        "يوليو",
        "أغسطس",
        "سبتمبر",
        "أكتوبر",
        "نوفمبر",
        "ديسمبر"
    ]


    # =====================================================
    # SELECT SALARY YEAR / MONTH
    # =====================================================

    # الدورة الافتراضية تظل نفس الدورة الحالية.
    if today.day >= 26:
        default_cycle_month = today.month + 1
        default_cycle_year = today.year

        if default_cycle_month == 13:
            default_cycle_month = 1
            default_cycle_year += 1
    else:
        default_cycle_month = today.month
        default_cycle_year = today.year


    select_col1, select_col2 = st.columns(2)

    with select_col1:

        cycle_year = st.selectbox(
            "📆 اختر السنة",
            options=list(range(today.year, 2101)),
            index=list(range(today.year, 2101)).index(default_cycle_year),
            key="salary_cycle_year"
        )

    with select_col2:

        cycle_month = st.selectbox(
            "📅 اختر الشهر",
            options=list(range(1, 13)),
            index=default_cycle_month - 1,
            format_func=lambda month: month_names[month - 1],
            key="salary_cycle_month"
        )


    # =====================================================
    # CALCULATE CYCLE DATES
    # =====================================================

    # دورة المرتب من يوم 26 إلى يوم 25
    if cycle_month == 1:
        previous_month = 12
        previous_year = cycle_year - 1
    else:
        previous_month = cycle_month - 1
        previous_year = cycle_year


    start_date = datetime.date(
        previous_year,
        previous_month,
        26
    )


    end_date = datetime.date(
        cycle_year,
        cycle_month,
        25
    )


    # =====================================================
    # CYCLE HEADER
    # =====================================================

    st.subheader(
        f"📅 دورة مرتب {month_names[cycle_month - 1]} {cycle_year}"
    )

    st.write(
        f"من **{start_date.strftime('%d/%m/%Y')}** "
        f"إلى **{end_date.strftime('%d/%m/%Y')}**"
    )


    # =====================================================
    # GET MONTHLY SALARY
    # =====================================================

    try:

        salary_result = (
            supabase
            .table("monthly_salary")
            .select("*")
            .eq("user_id", user_id)
            .eq("month", cycle_month)
            .eq("year", cycle_year)
            .limit(1)
            .execute()
        )

    except Exception as e:

        st.error(
            "حدث خطأ أثناء قراءة بيانات المرتب"
        )

        st.exception(e)
        st.stop()


    salary_data = None

    if salary_result.data:

        salary_data = salary_result.data[0]


    # =====================================================
    # SALARY INFORMATION
    # =====================================================

    st.subheader(
        "💰 بيانات المرتب لهذا الشهر"
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        basic_salary = st.number_input(
            "الراتب الأساسي",
            min_value=0.0,
            value=float(
                salary_data["basic_salary"]
                if salary_data
                else 0
            ),
            step=100.0
        )


        attendance_bonus = st.number_input(
            "بدل الانتظام",
            min_value=0.0,
            value=float(
                salary_data["attendance_bonus"]
                if salary_data
                else 0
            ),
            step=100.0
        )


        night_allowance = st.number_input(
            "بدل السهر / اليوم",
            min_value=0.0,
            value=float(
                salary_data["night_allowance"]
                if salary_data
                else 0
            ),
            step=10.0
        )


    with col2:

        target1_reward = st.number_input(
            "قيمة التارجت الأول",
            min_value=0.0,
            value=float(
                salary_data["target1_reward"]
                if salary_data
                else 40
            ),
            step=1.0
        )


        target2_reward = st.number_input(
            "قيمة التارجت الثاني",
            min_value=0.0,
            value=float(
                salary_data["target2_reward"]
                if salary_data
                else 50
            ),
            step=1.0
        )


        target3_reward = st.number_input(
            "قيمة التارجت الثالث",
            min_value=0.0,
            value=float(
                salary_data["target3_reward"]
                if salary_data
                else 77
            ),
            step=1.0
        )


    with col3:

        annual_leave = st.number_input(
            "عدد الإجازات السنوية",
            min_value=0,
            value=int(
                salary_data["annual_leave"]
                if salary_data
                else 0
            ),
            step=1
        )


    # =====================================================
    # SAVE SALARY
    # =====================================================

    if st.button(
        "💾 حفظ بيانات المرتب",
        use_container_width=True
    ):

        salary_record = {

            "user_id":
                user_id,

            "month":
                cycle_month,

            "year":
                cycle_year,

            "basic_salary":
                basic_salary,

            "attendance_bonus":
                attendance_bonus,

            "night_allowance":
                night_allowance,

            "target1_reward":
                target1_reward,

            "target2_reward":
                target2_reward,

            "target3_reward":
                target3_reward,

            "annual_leave":
                annual_leave
        }


        try:

            (
                supabase
                .table("monthly_salary")
                .upsert(
                    salary_record,
                    on_conflict="user_id,month,year"
                )
                .execute()
            )

            keep_latest_two_cycles()

            st.success(
                "✅ تم حفظ بيانات المرتب"
            )

        except Exception as e:

            st.error(
                "حدث خطأ أثناء حفظ بيانات المرتب"
            )

            st.exception(e)


    st.divider()


    # =====================================================
    # ATTENDANCE TABLE
    # =====================================================

    st.subheader(
        "📋 الحضور اليومي"
    )


    # =====================================================
    # CREATE CYCLE DATES
    # =====================================================

    dates = []

    current_date = start_date


    while current_date <= end_date:

        dates.append(current_date)

        current_date += datetime.timedelta(days=1)


    # =====================================================
    # GET ATTENDANCE DATA
    # =====================================================

    try:

        attendance_result = (
            supabase
            .table("attendance")
            .select("*")
            .eq("user_id", user_id)
            .eq("salary_month", cycle_month)
            .eq("salary_year", cycle_year)
            .execute()
        )

    except Exception as e:

        st.error(
            "حدث خطأ أثناء قراءة بيانات الحضور"
        )

        st.exception(e)
        st.stop()


    attendance_data = {

        row["attendance_date"]: row

        for row in attendance_result.data
    }


    # =====================================================
    # ATTENDANCE OPTIONS
    # =====================================================

    status_options = [
        "لم يتم التسجيل",
        "حاضر",
        "جمعة",
        "إجازة رسمية",
        "إجازة سنوية",
        "غياب بإذن",
        "غياب بدون إذن"
    ]


    hours_options = [
        "لا يوجد",
        "8 ساعات",
        "12 ساعة"
    ]


    target_options = [
        "لا يوجد",
        "الأول",
        "الثاني",
        "الثالث"
    ]


    # =====================================================
    # STATUS MAP
    # =====================================================

    status_map = {

        "not_recorded":
            "لم يتم التسجيل",

        "present":
            "حاضر",

        "friday":
            "جمعة",

        "official_holiday":
            "إجازة رسمية",

        "annual_leave":
            "إجازة سنوية",

        "absent_permission":
            "غياب بإذن",

        "absent_without_permission":
            "غياب بدون إذن"
    }


    target_map = {

        0:
            "لا يوجد",

        1:
            "الأول",

        2:
            "الثاني",

        3:
            "الثالث"
    }


    # =====================================================
    # BUILD ATTENDANCE DATA
    # =====================================================

    rows = []


    for date_value in dates:

        date_string = str(date_value)

        existing = attendance_data.get(
            date_string
        )


        if existing:

            status = status_map.get(
                existing["status"],
                "حاضر"
            )

            target = target_map.get(
                existing["target_level"],
                "لا يوجد"
            )

            saved_hours = existing.get(
                "work_hours"
            )

            if saved_hours == 8:
                work_hours = "8 ساعات"

            elif saved_hours == 12:
                work_hours = "12 ساعة"

            else:
                work_hours = "لا يوجد"

        else:

            status = "لم يتم التسجيل"

            target = "لا يوجد"

            work_hours = "لا يوجد"


        rows.append({

            "التاريخ":
                date_value,

            "اليوم":
                date_value.strftime("%A"),

            "حالة الحضور":
                status,

            "ساعات العمل":
                work_hours,

            "التارجت":
                target
        })


    df = pd.DataFrame(rows)


    # =====================================================
    # ATTENDANCE EDITOR
    # =====================================================

    edited_df = st.data_editor(

        df,

        use_container_width=True,

        hide_index=True,

        column_config={

            "التاريخ":
                st.column_config.DateColumn(
                    "التاريخ",
                    disabled=True
                ),

            "اليوم":
                st.column_config.TextColumn(
                    "اليوم",
                    disabled=True
                ),

            "حالة الحضور":
                st.column_config.SelectboxColumn(
                    "حالة الحضور",
                    options=status_options,
                    required=True
                ),

            "ساعات العمل":
                st.column_config.SelectboxColumn(
                    "ساعات العمل",
                    options=hours_options,
                    required=True
                ),

            "التارجت":
                st.column_config.SelectboxColumn(
                    "التارجت",
                    options=target_options,
                    required=True
                )
        },

        disabled=[
            "التاريخ",
            "اليوم"
        ],

        key=f"attendance_editor_{cycle_year}_{cycle_month}"
    )


    # =====================================================
    # ACTION BUTTONS
    # =====================================================

    save_col, preview_col = st.columns(2)

    with save_col:
        save_attendance_clicked = st.button(
            "💾 حفظ الحضور",
            use_container_width=True
        )

    with preview_col:
        preview_salary_clicked = st.button(
            "🧮 احسب المرتب بدون حفظ",
            use_container_width=True
        )

    # نخزن طلب المعاينة مؤقتًا لنفس التشغيل فقط.
    if preview_salary_clicked:
        st.session_state["preview_salary_requested"] = True

    # =====================================================
    # SAVE ATTENDANCE
    # =====================================================

    if save_attendance_clicked:

        status_reverse = {

            "لم يتم التسجيل":
                "not_recorded",

            "حاضر":
                "present",

            "جمعة":
                "friday",

            "إجازة رسمية":
                "official_holiday",

            "إجازة سنوية":
                "annual_leave",

            "غياب بإذن":
                "absent_permission",

            "غياب بدون إذن":
                "absent_without_permission"
        }


        target_reverse = {

            "لا يوجد":
                0,

            "الأول":
                1,

            "الثاني":
                2,

            "الثالث":
                3
        }


        try:

            for _, row in edited_df.iterrows():

                selected_status = row["حالة الحضور"]

                attendance_date = str(
                    row["التاريخ"]
                )


                # -------------------------------------------------
                # اليوم غير المسجل:
                # نحذفه من قاعدة البيانات لو كان محفوظًا من قبل
                # ولا نسجله مرة أخرى.
                # -------------------------------------------------

                if selected_status == "لم يتم التسجيل":

                    (
                        supabase
                        .table("attendance")
                        .delete()
                        .eq("user_id", user_id)
                        .eq("attendance_date", attendance_date)
                        .execute()
                    )

                    continue


                # -------------------------------------------------
                # تحويل ساعات العمل
                # -------------------------------------------------

                hours_value = row["ساعات العمل"]

                if (
                    pd.isna(hours_value)
                    or hours_value == "لا يوجد"
                ):
                    work_hours_value = None

                elif hours_value == "8 ساعات":
                    work_hours_value = 8

                elif hours_value == "12 ساعة":
                    work_hours_value = 12

                else:
                    work_hours_value = None


                # -------------------------------------------------
                # حالة الجمعة والإجازة الرسمية
                # -------------------------------------------------
                # لو لم يعمل الموظف:
                # ساعات العمل = NULL
                #
                # لو اشتغل:
                # ساعات العمل = 8 أو 12
                # -------------------------------------------------

                record = {

                    "user_id":
                        user_id,

                    "salary_month":
                        cycle_month,

                    "salary_year":
                        cycle_year,

                    "attendance_date":
                        attendance_date,

                    "status":
                        status_reverse[
                            selected_status
                        ],

                    "work_hours":
                        work_hours_value,

                    "target_level":
                        target_reverse[
                            row["التارجت"]
                        ]
                }


                (
                    supabase
                    .table("attendance")
                    .upsert(
                        record,
                        on_conflict="user_id,attendance_date"
                    )
                    .execute()
                )

            keep_latest_two_cycles()

            st.success(
                "✅ تم حفظ الحضور بنجاح"
            )

            st.rerun()


        except Exception as e:

            st.error(
                "حدث خطأ أثناء حفظ الحضور"
            )

            st.exception(e)


    # =====================================================
    # SALARY CALCULATION
    # =====================================================

    st.divider()

    st.subheader("💰 المرتب حتى الآن")

    def prepare_salary_data(attendance_rows):
        """
        تحويل بيانات الحضور اليومية إلى counters
        تستخدمها دوال salary_calculations.py.
        """

        data = {
            "present_days_12": 0,
            "present_days_8": 0,

            "friday_worked_days_12": 0,
            "friday_worked_days_8": 0,

            "official_worked_days_12": 0,
            "official_worked_days_8": 0,

            "friday_off_days": 0,
            "official_holiday_off_days": 0,

            "annual_leave_days": 0,

            "permission_absence_days": 0,
            "without_permission_days": 0,

            "target1_count_12": 0,
            "target2_count_12": 0,
            "target3_count_12": 0,

            "target1_count_8": 0,
            "target2_count_8": 0,
            "target3_count_8": 0,
        }

        def add_target(target, hours):
            if hours not in (8, 12):
                return

            if target == 1:
                key = "target1_count_12" if hours == 12 else "target1_count_8"
                data[key] += 1

            elif target == 2:
                key = "target2_count_12" if hours == 12 else "target2_count_8"
                data[key] += 1

            elif target == 3:
                key = "target3_count_12" if hours == 12 else "target3_count_8"
                data[key] += 1

        for row in attendance_rows:

            status = row.get("status")
            hours = row.get("work_hours")
            target = row.get("target_level", 0) or 0

            # اليوم غير المسجل لا يدخل في أي حساب.
            if status == "not_recorded":
                continue

            # None = "لا يوجد"
            if hours is not None:
                try:
                    hours = int(hours)
                except (TypeError, ValueError):
                    hours = None

            # ---------------------------------------------
            # حاضر
            # ---------------------------------------------
            if status == "present":

                if hours == 12:
                    data["present_days_12"] += 1
                    add_target(target, 12)

                elif hours == 8:
                    data["present_days_8"] += 1
                    add_target(target, 8)

            # ---------------------------------------------
            # جمعة
            # ---------------------------------------------
            elif status == "friday":

                if hours == 12:
                    data["friday_worked_days_12"] += 1
                    add_target(target, 12)

                elif hours == 8:
                    data["friday_worked_days_8"] += 1
                    add_target(target, 8)

                else:
                    data["friday_off_days"] += 1

            # ---------------------------------------------
            # إجازة رسمية
            # ---------------------------------------------
            elif status == "official_holiday":

                if hours == 12:
                    data["official_worked_days_12"] += 1
                    add_target(target, 12)

                elif hours == 8:
                    data["official_worked_days_8"] += 1
                    add_target(target, 8)

                else:
                    data["official_holiday_off_days"] += 1

            # ---------------------------------------------
            # إجازة سنوية
            # ---------------------------------------------
            elif status == "annual_leave":
                data["annual_leave_days"] += 1

            # ---------------------------------------------
            # غياب بإذن
            # ---------------------------------------------
            elif status == "absent_permission":
                data["permission_absence_days"] += 1

            # ---------------------------------------------
            # غياب بدون إذن
            # ---------------------------------------------
            elif status == "absent_without_permission":
                data["without_permission_days"] += 1

        return data


    # =====================================================
    # PREVIEW SALARY WITHOUT SAVING
    # =====================================================

    if st.session_state.get(
        "preview_salary_requested",
        False
    ):

        # الطلب يُنفذ مرة واحدة فقط.
        st.session_state["preview_salary_requested"] = False

        try:

            status_reverse_preview = {
                "لم يتم التسجيل": "not_recorded",
                "حاضر": "present",
                "جمعة": "friday",
                "إجازة رسمية": "official_holiday",
                "إجازة سنوية": "annual_leave",
                "غياب بإذن": "absent_permission",
                "غياب بدون إذن": "absent_without_permission"
            }

            target_reverse_preview = {
                "لا يوجد": 0,
                "الأول": 1,
                "الثاني": 2,
                "الثالث": 3
            }

            preview_rows = []

            for _, row in edited_df.iterrows():

                selected_status = row["حالة الحضور"]

                if selected_status == "لم يتم التسجيل":
                    continue

                hours_value = row["ساعات العمل"]

                if pd.isna(hours_value) or hours_value == "لا يوجد":
                    work_hours_value = None
                elif hours_value == "8 ساعات":
                    work_hours_value = 8
                elif hours_value == "12 ساعة":
                    work_hours_value = 12
                else:
                    work_hours_value = None

                preview_rows.append({
                    "attendance_date": str(row["التاريخ"]),
                    "status": status_reverse_preview[selected_status],
                    "work_hours": work_hours_value,
                    "target_level": target_reverse_preview.get(
                        row["التارجت"], 0
                    )
                })

            preview_counts = prepare_salary_data(preview_rows)

            preview_cycle_days = (
                end_date - start_date
            ).days + 1

            # =================================================
            # DAY 31 - PREVIEW
            # =================================================
            # اليوم 31 له قيمة ثابتة = basic / 30.
            # لو تم العمل فيه: يضاف مرة واحدة كبند اليوم الزائد.
            # لو كان جمعة/إجازة رسمية وتم العمل:
            #   8 ساعات  -> +1 يوم للسهر
            #   12 ساعة -> +2 يوم للسهر
            # لو كان يوم عادي وغياب بإذن/بدون إذن:
            #   قيمة اليوم تدخل أولًا ثم خصم الغياب من السهر.
            preview_extra_day = 0
            preview_31st_night_days = 0

            preview_extra_row = next(
                (
                    row for row in preview_rows
                    if pd.to_datetime(
                        row["attendance_date"]
                    ).day == 31
                ),
                None
            )

            if preview_cycle_days == 31 and preview_extra_row:
                day31_status = preview_extra_row["status"]
                day31_hours = preview_extra_row["work_hours"]

                daily_basic = calculate_basic_daily(
                    basic_salary
                )

                # يوم 31 جمعة / إجازة رسمية
                if day31_status in (
                    "friday",
                    "official_holiday"
                ):
                    if day31_hours in (8, 12):
                        # قيمة اليوم 31 المستقلة مرة واحدة.
                        preview_extra_day = daily_basic

                        # زيادة السهر الخاصة بالجمعة/الإجازة.
                        preview_31st_night_days = (
                            2 if day31_hours == 12 else 1
                        )

                # يوم 31 عادي وتم العمل فيه.
                elif day31_status == "present":
                    if day31_hours in (8, 12):
                        preview_extra_day = daily_basic

                # يوم 31 + غياب بإذن:
                # قيمة اليوم 31 مستقلة، والخصم من السهر يتم
                # مرة واحدة فقط من preview_counts.
                elif day31_status == "absent_permission":
                    preview_extra_day = daily_basic
                    preview_31st_night_days = 0

                # يوم 31 + غياب بدون إذن:
                # قيمة اليوم 31 مستقلة، والخصم من السهر يتم
                # مرة واحدة فقط من preview_counts.
                elif day31_status == "absent_without_permission":
                    preview_extra_day = daily_basic
                    preview_31st_night_days = 0

            preview_basic_rows = [
                row for row in preview_rows
                if not (
                    preview_cycle_days == 31
                    and pd.to_datetime(
                        row["attendance_date"]
                    ).day == 31
                )
            ]

            preview_basic_counts = prepare_salary_data(
                preview_basic_rows
            )

            preview_basic_total = calculate_basic_salary(
                basic_salary,
                preview_basic_counts["present_days_12"],
                preview_basic_counts["present_days_8"],
                preview_basic_counts["friday_worked_days_12"],
                preview_basic_counts["friday_worked_days_8"],
                preview_basic_counts["official_worked_days_12"],
                preview_basic_counts["official_worked_days_8"],
                preview_basic_counts["friday_off_days"],
                preview_basic_counts["official_holiday_off_days"],
                preview_basic_counts["annual_leave_days"],
                preview_basic_counts["permission_absence_days"],
                preview_basic_counts["without_permission_days"]
            )

            # إعادة حساب الغياب من بيانات المعاينة نفسها حتى لا تضيع
            # حالة "غياب بإذن" عند الضغط على حساب بدون حفظ.
            # الغياب يؤثر على بدل السهر:
            # غياب بإذن       = خصم يوم أساسي واحد.
            # غياب بدون إذن   = خصم يومين أساسيين.
            preview_permission_absence_days = sum(
                1
                for row in preview_rows
                if row.get("status") == "absent_permission"
            )

            preview_without_permission_days = sum(
                1
                for row in preview_rows
                if row.get("status") == "absent_without_permission"
            )

            # =================================================
            # PREVIEW NIGHT ALLOWANCE
            # =================================================
            # نحسبه هنا مباشرة من بيانات المعاينة حتى لا يعتمد
            # على نسخة قديمة من salary_calculations.py.
            daily_basic_preview = calculate_basic_daily(
                basic_salary
            )

            preview_worked_days = (
                preview_counts["present_days_12"]
                + preview_counts["present_days_8"]
                + preview_counts["friday_worked_days_12"]
                + preview_counts["friday_worked_days_8"]
                + preview_counts["official_worked_days_12"]
                + preview_counts["official_worked_days_8"]
            )

            preview_normal_night = (
                night_allowance * preview_worked_days
            )

            preview_holiday_extra_days = (
                preview_counts["friday_worked_days_12"] * 2
                + preview_counts["friday_worked_days_8"] * 1
                + preview_counts["official_worked_days_12"] * 2
                + preview_counts["official_worked_days_8"] * 1
            )

            preview_absence_deduction_days = (
                preview_permission_absence_days
                + (preview_without_permission_days * 2)
            )

            # مهم:
            # غياب بإذن يخصم قيمة يوم أساسي من بدل السهر:
            # basic_salary / 30
            preview_absence_deduction = (
                daily_basic_preview * preview_absence_deduction_days
            )

            preview_night_total = (
                preview_normal_night
                + daily_basic_preview * preview_holiday_extra_days
                - preview_absence_deduction
            )

            preview_overtime_total = calculate_regular_overtime(
                basic_salary,
                preview_counts["present_days_12"],
                preview_counts["friday_worked_days_12"],
                preview_counts["official_worked_days_12"]
            )

            preview_target_total = calculate_target_bonus(
                preview_counts["target1_count_12"],
                preview_counts["target2_count_12"],
                preview_counts["target3_count_12"],
                preview_counts["target1_count_8"],
                preview_counts["target2_count_8"],
                preview_counts["target3_count_8"],
                target1_reward,
                target2_reward,
                target3_reward
            )

            preview_attendance_total = calculate_attendance_bonus(
                attendance_bonus,
                preview_counts["annual_leave_days"],
                preview_counts["permission_absence_days"],
                preview_counts["without_permission_days"]
            )

            preview_total = calculate_total_salary(
                preview_basic_total,
                preview_attendance_total,
                preview_night_total,
                preview_overtime_total,
                preview_target_total,
                preview_extra_day
            )

            st.divider()
            st.subheader("🔎 معاينة المرتب")

            st.info(
                "الحساب مبني على البيانات الموجودة حاليًا في الجدول فقط، "
                "ولم يتم حفظ أي تعديل في قاعدة البيانات."
            )

            preview_col1, preview_col2, preview_col3 = st.columns(3)

            with preview_col1:
                st.metric(
                    "الأساسي",
                    f"{preview_basic_total:,.2f} جنيه"
                )

            with preview_col2:
                st.metric(
                    "بدل السهر",
                    f"{preview_night_total:,.2f} جنيه"
                )

            with preview_col3:
                st.metric(
                    "الإضافي",
                    f"{preview_overtime_total:,.2f} جنيه"
                )

            preview_col4, preview_col5, preview_col6 = st.columns(3)

            with preview_col4:
                st.metric(
                    "التارجت",
                    f"{preview_target_total:,.2f} جنيه"
                )

            with preview_col5:
                st.metric(
                    "الانتظام",
                    f"{preview_attendance_total:,.2f} جنيه"
                )

            with preview_col6:
                st.metric(
                    "اليوم الزائد",
                    f"{preview_extra_day:,.2f} جنيه"
                )

            st.success(
                f"💰 المرتب المتوقع: {preview_total:,.2f} جنيه"
            )

        except Exception as e:

            st.error(
                "حدث خطأ أثناء معاينة المرتب"
            )

            st.exception(e)


    try:

        saved_attendance = (
            supabase
            .table("attendance")
            .select("*")
            .eq("user_id", user_id)
            .eq("salary_month", cycle_month)
            .eq("salary_year", cycle_year)
            .execute()
        )

        attendance_rows_for_salary = saved_attendance.data or []

        salary_counts = prepare_salary_data(
            attendance_rows_for_salary
        )

        # ---------------------------------------------
        # Extra day in a 31-day salary cycle
        # ---------------------------------------------
        cycle_days = (
            end_date - start_date
        ).days + 1

        # اليوم 31 نفسه، وليس آخر يوم في الدورة.
        extra_day_row = next(
            (
                row for row in attendance_rows_for_salary
                if pd.to_datetime(
                    row.get("attendance_date")
                ).day == 31
            ),
            None
        )

        extra_31st_day = 0
        day31_night_days = 0

        if cycle_days == 31 and extra_day_row:

            extra_status = extra_day_row.get("status")
            extra_hours = extra_day_row.get("work_hours")

            daily_basic = calculate_basic_daily(
                basic_salary
            )

            # جمعة / إجازة رسمية
            if extra_status in (
                "friday",
                "official_holiday"
            ):
                if extra_hours in (8, 12):
                    # قيمة اليوم 31 المستقلة مرة واحدة.
                    extra_31st_day = daily_basic

                    # الزيادة الخاصة بالجمعة/الإجازة تدخل السهر فقط.
                    day31_night_days = (
                        2 if int(extra_hours) == 12 else 1
                    )

            # يوم عادي وتم العمل.
            elif extra_status == "present":
                if extra_hours in (8, 12):
                    extra_31st_day = daily_basic

            # غياب بإذن:
            # قيمة اليوم 31 مستقلة، والخصم من السهر يتم
            # مرة واحدة فقط من salary_counts.
            elif extra_status == "absent_permission":
                extra_31st_day = daily_basic
                day31_night_days = 0

            # غياب بدون إذن:
            # قيمة اليوم 31 مستقلة، والخصم من السهر يتم
            # مرة واحدة فقط من salary_counts.
            elif extra_status == "absent_without_permission":
                extra_31st_day = daily_basic
                day31_night_days = 0

        # ---------------------------------------------
        # Basic Salary
        # ---------------------------------------------
        # اليوم الزائد لا يدخل ضمن الـ30 يوم الأساسي.
        # باقي الأيام فقط تدخل في حساب basic_total.

        # الأساسي ثابت بالقيمة التي أدخلها الموظف.
        # اليوم 31 يظل بندًا منفصلًا ولا يغيّر قيمة الأساسي.
        basic_rows = [
            row
            for row in attendance_rows_for_salary
            if not (
                cycle_days == 31
                and pd.to_datetime(
                    row.get("attendance_date")
                ).day == 31
            )
        ]

        basic_counts = prepare_salary_data(
            basic_rows
        )

        basic_total = calculate_basic_salary(
            basic_salary,

            basic_counts["present_days_12"],
            basic_counts["present_days_8"],

            basic_counts["friday_worked_days_12"],
            basic_counts["friday_worked_days_8"],

            basic_counts["official_worked_days_12"],
            basic_counts["official_worked_days_8"],

            basic_counts["friday_off_days"],
            basic_counts["official_holiday_off_days"],

            basic_counts["annual_leave_days"],

            basic_counts["permission_absence_days"],
            basic_counts["without_permission_days"],
        )

        # ---------------------------------------------
        # Night Allowance
        # ---------------------------------------------

        # بدل السهر:
        # غياب بإذن       = خصم يوم أساسي واحد.
        # غياب بدون إذن   = خصم يومين أساسيين.
        #
        # مهم:
        # زيادة الجمعة/الإجازة الرسمية محسوبة بالفعل من
        # friday_worked_days / official_worked_days.
        # لذلك لا نضيف day31_night_days مرة ثانية.
        night_total = calculate_night_allowance(
            night_allowance,

            salary_counts["present_days_12"],
            salary_counts["present_days_8"],

            salary_counts["friday_worked_days_12"],
            salary_counts["friday_worked_days_8"],

            salary_counts["official_worked_days_12"],
            salary_counts["official_worked_days_8"],

            salary_counts["permission_absence_days"],
            salary_counts["without_permission_days"],
            basic_salary,
            day31_night_days,
        )

        # ---------------------------------------------
        # Regular Overtime
        # ---------------------------------------------

        overtime_total = calculate_regular_overtime(
            basic_salary,

            salary_counts["present_days_12"],

            salary_counts["friday_worked_days_12"],

            salary_counts["official_worked_days_12"],
        )

        # ---------------------------------------------
        # Target
        # ---------------------------------------------

        target_total = calculate_target_bonus(
            salary_counts["target1_count_12"],
            salary_counts["target2_count_12"],
            salary_counts["target3_count_12"],

            salary_counts["target1_count_8"],
            salary_counts["target2_count_8"],
            salary_counts["target3_count_8"],

            target1_reward,
            target2_reward,
            target3_reward,
        )

        # ---------------------------------------------
        # Attendance / Regularity
        # ---------------------------------------------

        attendance_total = calculate_attendance_bonus(
            attendance_bonus,

            salary_counts["annual_leave_days"],

            salary_counts["permission_absence_days"],

            salary_counts["without_permission_days"],
        )

        # ---------------------------------------------
        # Total
        # ---------------------------------------------

        total_salary = calculate_total_salary(
            basic_total,
            attendance_total,
            night_total,
            overtime_total,
            target_total,
            extra_31st_day,
        )

        # ---------------------------------------------
        # Display
        # ---------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "الأساسي الثابت",
                f"{basic_salary:,.2f} جنيه"
            )

        with col2:
            st.metric(
                "بدل السهر",
                f"{night_total:,.2f} جنيه"
            )

        with col3:
            st.metric(
                "الإضافي",
                f"{overtime_total:,.2f} جنيه"
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            st.metric(
                "التارجت",
                f"{target_total:,.2f} جنيه"
            )

        with col5:
            st.metric(
                "الانتظام",
                f"{attendance_total:,.2f} جنيه"
            )

        with col6:
            st.metric(
                "اليوم الزائد",
                f"{extra_31st_day:,.2f} جنيه"
            )

        # الإجازات السنوية المتبقية
        # يتم خصم الأيام التي تم تسجيلها كإجازة سنوية
        # من إجمالي الإجازات السنوية لهذا الشهر.
        remaining_annual_leave = max(
            annual_leave - salary_counts["annual_leave_days"],
            0
        )

        st.metric(
            "الإجازات السنوية المتبقية",
            f"{remaining_annual_leave} يوم"
        )

        st.success(
            f"💰 المرتب حتى الآن: {total_salary:,.2f} جنيه"
        )

    except Exception as e:

        st.error(
            "حدث خطأ أثناء حساب المرتب"
        )

        st.exception(e)