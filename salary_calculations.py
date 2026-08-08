# =========================================================
# WorkPay - Salary Calculations
# =========================================================

DAILY_DIVISOR = 30


# =========================================================
# 1. Basic Salary Per Day
# =========================================================

def calculate_basic_daily(basic_salary):
    """
    قيمة اليوم الواحد من الراتب الأساسي.
    """
    return basic_salary / DAILY_DIVISOR


# =========================================================
# 2. Regular Overtime Per Day - 12 Hours
# =========================================================

def calculate_regular_overtime_daily(basic_salary):
    """
    الإضافي العادي لليوم العادي الذي يعمل فيه الموظف 12 ساعة.

    المعادلة:
    basic salary / 30 / 8 * 5
    """
    daily_salary = basic_salary / DAILY_DIVISOR
    hourly_salary = daily_salary / 8
    return hourly_salary * 5


# =========================================================
# 3. Calculate Basic Salary
# =========================================================

def calculate_basic_salary(
    basic_salary,
    present_days_12,
    present_days_8,
    friday_worked_days_12,
    friday_worked_days_8,
    official_worked_days_12,
    official_worked_days_8,
    friday_off_days,
    official_holiday_off_days,
    annual_leave_days,
    permission_absence_days,
    without_permission_days
):
    """
    الأساسي المدخل ثابت ولا يتغير بالحضور أو الغياب.
    """
    return basic_salary


# =========================================================
# 4. Night Allowance
# =========================================================

def calculate_night_allowance(
    night_allowance,
    present_days_12,
    present_days_8,
    friday_worked_days_12,
    friday_worked_days_8,
    official_worked_days_12,
    official_worked_days_8,
    *extra_args,
    permission_absence_days=0,
    without_permission_days=0,
    basic_salary=0,
    extra_31st_night_days=0
):
    """
    حساب بدل السهر.

    يوم عادي:
        بدل السهر العادي مرة واحدة.

    جمعة / إجازة رسمية مع العمل:
        8 ساعات  = السهر العادي + يوم أساسي واحد.
        12 ساعة = السهر العادي + يومين أساسيين.

    غياب بإذن:
        خصم يوم أساسي واحد من بدل السهر.

    غياب بدون إذن:
        خصم يومين أساسيين من بدل السهر.

    extra_31st_night_days:
        الزيادة الخاصة بالعمل في يوم 31 إذا كان جمعة/إجازة رسمية.
    """

    # Backward compatibility:
    # main.py may send the last 4 values positionally.
    if extra_args:
        if len(extra_args) >= 1:
            permission_absence_days = extra_args[0]
        if len(extra_args) >= 2:
            without_permission_days = extra_args[1]
        if len(extra_args) >= 3:
            basic_salary = extra_args[2]
        if len(extra_args) >= 4:
            extra_31st_night_days = extra_args[3]

    daily_basic = (
        calculate_basic_daily(basic_salary)
        if basic_salary
        else 0
    )

    worked_days = (
        present_days_12
        + present_days_8
        + friday_worked_days_12
        + friday_worked_days_8
        + official_worked_days_12
        + official_worked_days_8
    )

    # السهر العادي لكل يوم تم العمل فيه.
    normal_night_total = night_allowance * worked_days

    # زيادة الجمعة والإجازة الرسمية.
    holiday_extra_days = (
        (friday_worked_days_12 * 2)
        + friday_worked_days_8
        + (official_worked_days_12 * 2)
        + official_worked_days_8
    )

    # خصم الغياب من بدل السهر:
    # بإذن = يوم أساسي
    # بدون إذن = يومين أساسيين
    absence_deduction_days = (
        permission_absence_days
        + (without_permission_days * 2)
    )

    absence_deduction = daily_basic * absence_deduction_days

    # زيادة يوم 31 إذا كان جمعة/إجازة رسمية وتم العمل.
    day31_extra_night = daily_basic * extra_31st_night_days

    return (
        normal_night_total
        + (daily_basic * holiday_extra_days)
        + day31_extra_night
        - absence_deduction
    )


# =========================================================
# 5. Regular Overtime
# =========================================================

def calculate_regular_overtime(
    basic_salary,
    present_days_12,
    friday_worked_days_12,
    official_worked_days_12
):
    """
    الإضافي العادي لأيام العمل العادية 12 ساعة فقط.

    الجمعة والإجازة الرسمية:
        لا يوجد إضافي.
    """
    overtime_daily = calculate_regular_overtime_daily(basic_salary)
    return overtime_daily * present_days_12


# =========================================================
# 6. Target Bonus
# =========================================================

def calculate_target_bonus(
    target1_count_12,
    target2_count_12,
    target3_count_12,
    target1_count_8,
    target2_count_8,
    target3_count_8,
    target1_value,
    target2_value,
    target3_value
):
    """
    12 ساعة = القيمة كاملة.
    8 ساعات = نصف القيمة.
    """

    target1_total = (
        target1_count_12 * target1_value
        + target1_count_8 * (target1_value / 2)
    )

    target2_total = (
        target2_count_12 * target2_value
        + target2_count_8 * (target2_value / 2)
    )

    target3_total = (
        target3_count_12 * target3_value
        + target3_count_8 * (target3_value / 2)
    )

    return target1_total + target2_total + target3_total


# =========================================================
# 7. Attendance Bonus / Regularity
# =========================================================

def calculate_attendance_bonus(
    attendance_bonus,
    annual_leave_days,
    permission_absence_days,
    without_permission_days
):
    """
    الانتظام:

    0 أيام مؤثرة = كامل
    1 يوم = -200
    2 أيام = -500
    3 أيام أو أكثر = صفر
    """

    affecting_days = (
        annual_leave_days
        + permission_absence_days
        + without_permission_days
    )

    if affecting_days == 0:
        return attendance_bonus

    if affecting_days == 1:
        return max(attendance_bonus - 200, 0)

    if affecting_days == 2:
        return max(attendance_bonus - 500, 0)

    return 0


# =========================================================
# 8. Extra Day - 31 Day Cycle
# =========================================================

def calculate_31st_day(
    basic_salary,
    cycle_days,
    is_31st_day_worked,
    work_hours,
    is_friday=False,
    is_official_holiday=False
):
    """
    قيمة اليوم 31 المستقلة.
    """
    if cycle_days != 31:
        return 0

    if not is_31st_day_worked:
        return 0

    if work_hours not in (8, 12):
        return 0

    return calculate_basic_daily(basic_salary)


# =========================================================
# 9. Total Salary
# =========================================================

def calculate_total_salary(
    basic_salary_total,
    attendance_bonus,
    night_allowance_total,
    regular_overtime_total,
    target_bonus_total,
    extra_31st_day
):
    """
    إجمالي المرتب النهائي.
    """
    return (
        basic_salary_total
        + attendance_bonus
        + night_allowance_total
        + regular_overtime_total
        + target_bonus_total
        + extra_31st_day
    )