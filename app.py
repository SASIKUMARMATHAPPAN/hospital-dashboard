import streamlit as st
import pandas as pd
from groq import Groq

# Page Setup
st.set_page_config(page_title="Hospital AI Dashboard & Chatbot", layout="wide")
st.title("🏥 Hospital Data Autonomous AI Dashboard & Chatbot")

# --- AUTO LOAD API KEY FROM STREAMLIT SECRETS OR DEFAULT ---
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    groq_api_key = "YOUR_API_KEY_HERE"  # Safe dummy key for GitHub security

# Sidebar Connection Status
st.sidebar.header("🔑 AI Configuration")
if groq_api_key and groq_api_key != "YOUR_API_KEY_HERE":
    st.sidebar.success("AI Model Connected Successfully! ✅")
else:
    st.sidebar.warning("API Key missing or using placeholder! Please configure Streamlit Secrets.")

st.sidebar.markdown("---")
st.sidebar.header("📌 Data Filters")

# File Upload Section
uploaded_file = st.file_uploader("Upload Hospital Excel Sheet", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Read Dataset
    df = pd.read_excel(uploaded_file)
    
    # Date processing if Date column exists
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df['Day_Name'] = df['Date'].dt.day_name()
        df['Week_Year'] = df['Date'].dt.strftime('%Y-W%U')
        df['Month_Year'] = df['Date'].dt.strftime('%Y-%m')
        
        min_date = df['Date'].min().date()
        max_date = df['Date'].max().date()
        selected_date = st.sidebar.date_input("Filter by Date Range:", [min_date, max_date])
        
        if len(selected_date) == 2:
            start_date, end_date = selected_date
            filtered_df = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)]
        else:
            filtered_df = df.copy()
    else:
        filtered_df = df.copy()

    st.success("File uploaded successfully!")

    # Department Filter
    if 'Department' in df.columns:
        departments = ['All'] + list(df['Department'].dropna().unique())
        selected_dept = st.sidebar.selectbox("Filter by Department:", departments)
        if selected_dept != 'All':
            filtered_df = filtered_df[filtered_df['Department'] == selected_dept]

    # ====================================================
    # 1. AI CHATBOT INTEGRATION (PLACED AT THE ABSOLUTE TOP)
    # ====================================================
    st.markdown("---")
    st.subheader("🤖 Hospital AI Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display past chat messages inside isolated chat containers
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_prompt := st.chat_input("Ask anything about the uploaded hospital dataset..."):
        if not groq_api_key or groq_api_key == "YOUR_API_KEY_HERE":
            st.error("Please configure your Groq API Key in Streamlit Secrets to chat!")
        else:
            # Append user message
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            data_summary = filtered_df.describe(include='all').to_string()
            data_sample = filtered_df.head(15).to_string()

            client = Groq(api_key=groq_api_key)

            system_instruction = f"""
            You are an expert AI medical assistant for a hospital dashboard. 
            Answer the user's question accurately using the provided hospital dataset summary and sample rows.
            Provide detailed breakdowns, percentages, or exact numbers whenever requested.
            
            Dataset Overview & Summary:
            {data_summary}

            Sample Data Rows:
            {data_sample}
            """

            models_to_try = [
                "llama-3.3-70b-versatile",
                "openai/gpt-oss-20b"
            ]

            response = None
            last_error = None

            for model_name in models_to_try:
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_prompt}
                        ],
                    )
                    break
                except Exception as err:
                    last_error = err
                    continue

            if response is not None:
                ai_response = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                # Render AI response in its own distinct chat card container
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
            else:
                st.error(f"Error fetching response from Groq API: {last_error}")

    # ====================================================
    # 2. DASHBOARD METRICS (NOW BELOW AI CHAT)
    # ====================================================
    st.markdown("---")
    st.subheader("📊 Key Metrics & Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", len(filtered_df))
    
    if 'Patient_ID' in filtered_df.columns:
        col2.metric("Total Patients", filtered_df['Patient_ID'].nunique())
    elif 'Patient Name' in filtered_df.columns:
        col2.metric("Total Patients", filtered_df['Patient Name'].nunique())
    else:
        col2.metric("Total Rows", len(filtered_df))

    if 'Cost' in filtered_df.columns:
        col3.metric("Total Cost", f"₹{filtered_df['Cost'].sum():,.2f}")
    elif 'Bill Amount' in filtered_df.columns:
        col3.metric("Total Bill", f"₹{filtered_df['Bill Amount'].sum():,.2f}")

    if 'Age' in filtered_df.columns:
        col4.metric("Avg Patient Age", f"{filtered_df['Age'].mean():.1f} yrs")

    # Preview Filtered Data
    with st.expander("🔍 View Raw Dataset", expanded=False):
        st.dataframe(filtered_df, use_container_width=True)

    # ====================================================
    # 3. RATIOS & TIME-WISE ANALYTICS CHARTS
    # ====================================================
    st.markdown("---")
    st.subheader("📈 Time-Wise Analytics & Ratios")
    
    if 'Date' in filtered_df.columns:
        t_col1, t_col2 = st.columns(2)
        
        with t_col1:
            st.write("### 📅 Day-Wise Records")
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_counts = filtered_df['Day_Name'].value_counts().reindex(day_order).fillna(0)
            st.bar_chart(day_counts)

        with t_col2:
            st.write("### 🗓️ Month-Wise Records")
            month_counts = filtered_df['Month_Year'].value_counts().sort_index()
            st.bar_chart(month_counts)

        st.write("### 📊 Week-Wise Records")
        week_counts = filtered_df['Week_Year'].value_counts().sort_index()
        st.bar_chart(week_counts)

    # Department & Status Ratios
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        if 'Department' in filtered_df.columns:
            st.write("### 🏢 Department Ratio & Count")
            dept_counts = filtered_df['Department'].value_counts().reset_index()
            dept_counts.columns = ['Department', 'Count']
            dept_counts['Percentage (%)'] = ((dept_counts['Count'] / dept_counts['Count'].sum()) * 100).round(2)
            st.dataframe(dept_counts, use_container_width=True)
            st.bar_chart(data=dept_counts, x='Department', y='Count')

    with chart_col2:
        if 'Status' in filtered_df.columns:
            st.write("### 🏥 Patient Status Ratio")
            status_counts = filtered_df['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            status_counts['Percentage (%)'] = ((status_counts['Count'] / status_counts['Count'].sum()) * 100).round(2)
            st.dataframe(status_counts, use_container_width=True)
            st.bar_chart(data=status_counts, x='Status', y='Count')

else:
    st.info("Please upload an Excel file to load the chatbot, dashboard, and analytics.")