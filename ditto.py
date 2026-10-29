import altair as alt
import itertools
import pandas as pd
import requests
import streamlit as st

# Page configuration
st.set_page_config(page_title="Ditto term matrix", layout="wide")

# Custom CSS for bigger fonts and removing table inner scrollbars
st.markdown(
    """
    <style>
    h1 { font-size: 2.8rem !important; color: #1E3A8A; }
    h2 { font-size: 2.2rem !important; }
    h3 { font-size: 1.6rem !important; }
    .stTextInput label, .stSelectbox label, .stNumberInput label { font-size: 1.1rem !important; font-weight: 600; }
    
    /* Remove internal scrollbar from dataframe and expand fully */
    div[data-testid="stDataFrame"] > div {
        max-height: none !important;
    }
    div[data-testid="stDataFrame"] table {
        height: auto !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🛡️ Ditto term matrix")
st.markdown(
    "##### Automate premium calculations across multiple age, cover, and"
    " products instantly."
)
st.write("")

# --- Inputs Section ---
col_input1, col_input2, col_input3 = st.columns(3)

with col_input1:
  st.subheader("Age Configuration")
  age_mode = st.radio(
      "Choose Age Input Type:", ["Comma Separated", "Range (e.g. 60 to 70)"]
  )

  if age_mode == "Comma Separated":
    ages_str = st.text_input("Enter Ages", "65, 66, 67, 68, 69, 70")
  else:
    col_r1, col_r2 = st.columns(2)
    with col_r1:
      start_age = st.number_input("Start Age", value=65, min_value=18, max_value=99)
    with col_r2:
      end_age = st.number_input("End Age", value=70, min_value=18, max_value=100)

with col_input2:
  st.subheader("Cover Amount Configuration")
  covers_str = st.text_input(
      "Cover Amounts in Crores (comma separated)", "2.5, 3.0"
  )

with col_input3:
  st.subheader("Insurance Product")
  product_options = {
      "HDFC (Click 2 Protect Supreme Plus)": "CLICK_2_PROTECT_SUPREME_PLUS",
      "ICICI (I-Protect Smart Plus)": "I_PROTECT_SMART_PLUS",
      "Axis (Smart Term Plan Plus)": "SMART_TERM_PLAN_PLUS",
      "Bajaj (E-Touch)": "E_TOUCH",
  }
  selected_product_label = st.selectbox(
      "Choose Product", list(product_options.keys()), index=0
  )
  selected_product_code = product_options[selected_product_label]

# --- Advanced Settings Dropdown ---
with st.expander("⚙️ Advanced Settings (Payload Parameters)"):
  st.write(
      "Modify default profile parameters sent to Ditto's backend payload."
  )
  col_a, col_b, col_c = st.columns(3)
  with col_a:
    ann_inc = st.number_input("Annual Income", value=1900000)
    m_expenses = st.number_input("Monthly Expenses", value=25000)
    pincode = st.number_input("Pincode", value=600119)
  with col_b:
    salaried = st.selectbox("Salaried", [True, False])
    tobacco = st.selectbox("Tobacco Consumer", [False, True])
    diabetic = st.selectbox("Diabetic", [False, True])
  with col_c:
    gender = st.selectbox("Gender", ["Male", "Female"])
    dob = st.text_input("Date of Birth (YYYY-MM-DD)", value="1999-11-21")
    payment_freq = st.selectbox("Payment Frequency", ["Yearly", "Monthly"])

st.write("")


# Cached function to fetch data from API without re-triggering unnecessarily
@st.cache_data(show_spinner=False)
def fetch_insurance_data(
    ages,
    covers,
    product_code,
    ann_inc,
    m_expenses,
    pincode,
    salaried,
    tobacco,
    diabetic,
    gender,
    dob,
    payment_freq,
):
  url = "https://api.joinditto.in/life/v2/premium/estimate"
  headers = {
      "Content-Type": "application/json",
      "Origin": "https://app.joinditto.in",
      "Referer": "https://app.joinditto.in/",
      "User-Agent": "Mozilla/5.0",
  }

  results = []
  for age, cover_amt in itertools.product(ages, covers):
    payload = {
        "annInc": ann_inc,
        "mExpenses": m_expenses,
        "pincode": pincode,
        "salaried": salaried,
        "tobacco": tobacco,
        "diabetic": diabetic,
        "dob": dob,
        "education": "graduate",
        "gender": gender,
        "gst_waiver": False,
        "is_nri": False,
        "paymentFreq": payment_freq,
        "products": [product_code],
        "tillAge": age,
        "cover": cover_amt,
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
      data = response.json()
      try:
        product_data = data["data"]["products"][0]
        results.append({
            "Cover_Till_Age": age,
            "Cover_Amount_Cr": cover_amt / 10000000,
            "First_Year_With_Discount": product_data["basePlan"]["base"],
            "Standard_Without_Discount": product_data["secondYearPremium"][
                "base"
            ],
        })
      except (KeyError, IndexError):
        pass
  return results


# --- Calculate Button & Session State Storage ---
if st.button("🚀 Calculate, Compare & Plot", use_container_width=True):
  try:
    if age_mode == "Comma Separated":
      ages_list = [int(a.strip()) for a in ages_str.split(",")]
    else:
      ages_list = list(range(int(start_age), int(end_age) + 1))

    covers_list = [
        int(float(c.strip()) * 10000000) for c in covers_str.split(",")
    ]
  except ValueError:
    st.error("Please enter valid numbers for ages and cover amounts.")
    st.stop()

  with st.spinner(f"Fetching {selected_product_label} quotes from Ditto API..."):
    raw_data = fetch_insurance_data(
        tuple(ages_list),
        tuple(covers_list),
        selected_product_code,
        ann_inc,
        m_expenses,
        pincode,
        salaried,
        tobacco,
        diabetic,
        gender,
        dob,
        payment_freq,
    )

  if raw_data:
    st.session_state["df_raw"] = pd.DataFrame(raw_data)
  else:
    st.error(
        "No results fetched for this product. Check your network or payload"
        " parameters."
    )

# --- Render Results if Data Exists in Session State ---
if "df_raw" in st.session_state and not st.session_state["df_raw"].empty:
  df_raw = st.session_state["df_raw"]

  st.markdown("---")
  st.subheader(
      f"📊 Unified Comparison Table ({selected_product_label} Quotes)"
  )

  # Interactive Sorting Controls
  sort_col1, sort_col2 = st.columns(2)
  with sort_col1:
    sort_column = st.selectbox(
        "Sort Table By Column:",
        [
            "Cover_Till_Age",
            "Cover_Amount_Cr",
            "Standard_Without_Discount",
            "First_Year_With_Discount",
        ],
        key="sort_column_key",
    )
  with sort_col2:
    sort_order = st.radio(
        "Sort Order:",
        ["Ascending (Low to High)", "Descending (High to Low)"],
        key="sort_order_key",
    )

  is_ascending = True if "Ascending" in sort_order else False

  # Multi-level sort: Primary is user selection, Secondary tie-breaker is always Standard_Without_Discount (Ascending)
  if sort_column == "Standard_Without_Discount":
    sort_cols = [sort_column]
    sort_dirs = [is_ascending]
  else:
    sort_cols = [sort_column, "Standard_Without_Discount"]
    sort_dirs = [is_ascending, True]

  df = df_raw.sort_values(by=sort_cols, ascending=sort_dirs).reset_index(
      drop=True
  )

  # Calculate active difference based on the Standard Without Discount price
  df["diff_numeric"] = df["Standard_Without_Discount"].diff()


  def format_diff(val):
    if pd.isnull(val):
      return "N/A"
    return f"+{int(val)}" if val > 0 else f"{int(val)}"


  df["Formatted_Diff"] = df["diff_numeric"].apply(format_diff)


  def color_diff(val):
    if pd.isnull(val):
      return ""
    try:
      num = float(val)
      color = "green" if num < 0 else "red"
      return f"color: {color}; font-weight: bold;"
    except ValueError:
      return ""


  # Display styled master table using map() instead of applymap()
  styled_df = (
      df[[
          "Cover_Till_Age",
          "Cover_Amount_Cr",
          "First_Year_With_Discount",
          "Standard_Without_Discount",
          "Formatted_Diff",
      ]]
      .style.map(color_diff, subset=["Formatted_Diff"])
      .format({
          "Cover_Amount_Cr": "{:.1f} Cr",
          "First_Year_With_Discount": "₹{:,.0f}",
          "Standard_Without_Discount": "₹{:,.0f}",
      })
  )

  row_count = len(df)
  table_height = min(max(150, row_count * 35 + 40), 1000)
  st.dataframe(styled_df, use_container_width=True, height=table_height)

  # --- High-Contrast Altair Graph at the Bottom ---
  st.markdown("---")
  st.subheader("📈 Unified Trend Graph (Zoomed Scale)")
  st.write(
      "Y-axis range is dynamically zoomed to highlight highs, lows, and"
      " intersection points clearly."
  )

  chart_data = df_raw.copy()
  chart_data["Cover_Tier"] = chart_data["Cover_Amount_Cr"].astype(str) + " Cr"

  min_val = chart_data["Standard_Without_Discount"].min() * 0.95
  max_val = chart_data["Standard_Without_Discount"].max() * 1.05

  chart = (
      alt.Chart(chart_data)
      .mark_line(point=True, strokeWidth=3)
      .encode(
          x=alt.X(
              "Cover_Till_Age:O",
              title="Cover Till Age",
              axis=alt.Axis(labelAngle=0),
          ),
          y=alt.Y(
              "Standard_Without_Discount:Q",
              title="Standard Premium (₹)",
              scale=alt.Scale(domain=[min_val, max_val]),
          ),
          color=alt.Color("Cover_Tier:N", title="Cover Amount"),
          tooltip=[
              "Cover_Till_Age",
              "Cover_Tier",
              "Standard_Without_Discount",
              "First_Year_With_Discount",
          ],
      )
      .properties(height=450)
      .interactive()
  )

  st.altair_chart(chart, use_container_width=True)
