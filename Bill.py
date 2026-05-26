import streamlit as st
import sqlite3
import pandas as pd

# =========================================
# DATABASE CONNECTION
# =========================================

conn = sqlite3.connect(
    "inventory_app.db",
    check_same_thread=False
)

cursor = conn.cursor()

# =========================================
# CREATE TABLES
# =========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT UNIQUE,
    opening_qty REAL,
    available_qty REAL,
    rate REAL,
    unit TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS billing (
    invoice_no INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_date TEXT,
    buyer_name TEXT,
    product_name TEXT,
    quantity REAL,
    rate REAL,
    total_amount REAL
)
""")

conn.commit()

# =========================================
# PRODUCT MASTER LIST
# =========================================

product_master = [
    "TMT 8MM",
    "TMT 10MM",
    "TMT 12MM",
    "TMT 16MM",
    "TMT 20MM",
    "Iron Ore",
    "Coal",
    "Billets",
    "Scrap"
]

# =========================================
# PAGE CONFIG
# =========================================

st.set_page_config(
    page_title="Inventory Billing App",
    layout="wide"
)

st.title("📦 Inventory & Billing Management")

# =========================================
# SIDEBAR MENU
# =========================================

menu = st.sidebar.radio(
    "Select Option",
    [
        "Add Inventory",
        "View Inventory",
        "Create Bill",
        "Billing Report",
        "Download Daily Excel",
        "Clear Complete Data"
    ]
)

# =========================================
# ADD INVENTORY
# =========================================

if menu == "Add Inventory":

    st.header("➕ Add Opening Inventory")

    with st.form("inventory_form"):

        product_name = st.selectbox(
            "Select Product",
            product_master
        )

        opening_qty = st.number_input(
            "Opening Quantity",
            min_value=0.0
        )

        rate = st.number_input(
            "Rate",
            min_value=0.0
        )

        unit = st.selectbox(
            "Unit",
            ["KG", "MT", "PCS", "TON"]
        )

        submit_inventory = st.form_submit_button(
            "Add Inventory"
        )

        if submit_inventory:

            # CHECK IF PRODUCT ALREADY EXISTS
            cursor.execute("""
            SELECT opening_qty,
                   available_qty
            FROM inventory
            WHERE product_name = ?
            """, (product_name,))

            existing = cursor.fetchone()

            # IF EXISTS → UPDATE QTY
            if existing:

                new_opening = (
                    existing[0] + opening_qty
                )

                new_available = (
                    existing[1] + opening_qty
                )

                cursor.execute("""
                UPDATE inventory
                SET opening_qty = ?,
                    available_qty = ?,
                    rate = ?,
                    unit = ?
                WHERE product_name = ?
                """, (
                    new_opening,
                    new_available,
                    rate,
                    unit,
                    product_name
                ))

                conn.commit()

                st.success(
                    "Inventory Updated Successfully"
                )

            # NEW PRODUCT
            else:

                cursor.execute("""
                INSERT INTO inventory(
                    product_name,
                    opening_qty,
                    available_qty,
                    rate,
                    unit
                )
                VALUES (?, ?, ?, ?, ?)
                """, (
                    product_name,
                    opening_qty,
                    opening_qty,
                    rate,
                    unit
                ))

                conn.commit()

                st.success(
                    "Inventory Added Successfully"
                )

# =========================================
# VIEW INVENTORY
# =========================================

elif menu == "View Inventory":

    st.header("📋 Current Inventory")

    df_inventory = pd.read_sql_query(
        "SELECT * FROM inventory",
        conn
    )

    st.dataframe(
        df_inventory,
        use_container_width=True
    )

# =========================================
# CREATE BILL
# =========================================

elif menu == "Create Bill":

    st.header("🧾 Create Sales Bill")

    products_df = pd.read_sql_query(
        "SELECT product_name FROM inventory",
        conn
    )

    product_list = products_df[
        "product_name"
    ].tolist()

    if len(product_list) == 0:

        st.warning(
            "Please Add Inventory First"
        )

    else:

        with st.form("billing_form"):

            invoice_date = st.date_input(
                "Invoice Date"
            )

            buyer_name = st.text_input(
                "Buyer Name"
            )

            product_name = st.selectbox(
                "Select Product",
                product_list
            )

            quantity = st.number_input(
                "Quantity",
                min_value=0.0
            )

            generate_bill = st.form_submit_button(
                "Generate Bill"
            )

            if generate_bill:

                cursor.execute("""
                SELECT available_qty,
                       rate
                FROM inventory
                WHERE product_name = ?
                """, (product_name,))

                result = cursor.fetchone()

                if result:

                    available_qty = result[0]
                    rate = result[1]

                    if quantity > available_qty:

                        st.error(
                            "Insufficient Inventory"
                        )

                    else:

                        total_amount = (
                            quantity * rate
                        )

                        # INSERT BILL
                        cursor.execute("""
                        INSERT INTO billing(
                            invoice_date,
                            buyer_name,
                            product_name,
                            quantity,
                            rate,
                            total_amount
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            str(invoice_date),
                            buyer_name,
                            product_name,
                            quantity,
                            rate,
                            total_amount
                        ))

                        # UPDATE STOCK
                        new_stock = (
                            available_qty - quantity
                        )

                        cursor.execute("""
                        UPDATE inventory
                        SET available_qty = ?
                        WHERE product_name = ?
                        """, (
                            new_stock,
                            product_name
                        ))

                        conn.commit()

                        st.success(
                            "Bill Generated Successfully"
                        )

                        st.subheader(
                            f"Total Amount: ₹{total_amount}"
                        )

                        st.subheader(
                            f"Remaining Stock: {new_stock}"
                        )

# =========================================
# BILLING REPORT
# =========================================

elif menu == "Billing Report":

    st.header("📊 Billing Report")

    billing_df = pd.read_sql_query("""
    SELECT *
    FROM billing
    ORDER BY invoice_no DESC
    """, conn)

    st.dataframe(
        billing_df,
        use_container_width=True
    )

# =========================================
# EXPORT DAILY REPORT
# =========================================

elif menu == "Download Daily Excel":

    st.header("📥 Export Daily Excel")

    selected_date = st.date_input(
        "Select Date"
    )

    if st.button("Generate Excel Report"):

        query = """
        SELECT *
        FROM billing
        WHERE invoice_date = ?
        """

        report_df = pd.read_sql_query(
            query,
            conn,
            params=(str(selected_date),)
        )

        if report_df.empty:

            st.warning(
                "No Billing Found"
            )

        else:

            file_name = (
                f"Daily_Report_{selected_date}.xlsx"
            )

            report_df.to_excel(
                file_name,
                index=False
            )

            with open(file_name, "rb") as file:

                st.download_button(
                    label="Download Excel File",
                    data=file,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            st.success(
                "Excel Report Generated"
            )

# =========================================
# CLEAR COMPLETE DATA
# =========================================

elif menu == "Clear Complete Data":

    st.header("⚠️ Clear Complete Data")

    st.warning(
        "This will delete ALL inventory and billing data."
    )

    confirm = st.checkbox(
        "I Confirm To Delete Complete Data"
    )

    if confirm:

        if st.button("Delete All Data"):

            cursor.execute(
                "DELETE FROM inventory"
            )

            cursor.execute(
                "DELETE FROM billing"
            )

            conn.commit()

            st.success(
                "Complete Data Deleted Successfully"
            )

# =========================================
# FOOTER
# =========================================

st.sidebar.success(
    "Inventory System Running Successfully"
)
