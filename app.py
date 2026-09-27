import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Solo System - Study Tracker", page_icon="📊", layout="wide"
)


# Initialize Database connection using Streamlit's connection manager
def get_connection():
  # This connects to Supabase using the secrets.toml configuration
  return st.connection("supabase", type="sql")


def init_db():
  conn = get_connection()
  # Create tables in PostgreSQL (Supabase) if they don't exist
  with conn.session as s:
    s.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                chapter_id SERIAL PRIMARY KEY,
                chapter_name TEXT UNIQUE,
                subject TEXT
            );
        """)
    s.execute("""
            CREATE TABLE IF NOT EXISTS daily_practice_v2 (
                day_num INT,
                date_or_context TEXT,
                chapter_name TEXT,
                questions_solved INT,
                PRIMARY KEY (day_num, chapter_name)
            );
        """)
    s.commit()


def main():
  st.title("🎯 Solo System: Advanced Study & Chapter Progress Tracker")
  init_db()
  conn = get_connection()

  # Create Tabs for Clean Separation
  tab1, tab2, tab3 = st.tabs(
      [
          "📚 Chapters Manager",
          "📅 Daily Question Logging",
          "📈 Overall Analytics",
      ]
  )

  # --- TAB 1: CHAPTERS MANAGER ---
  with tab1:
    st.markdown("### Add Your Study Chapters")
    with st.form("add_chapter_form"):
      c_name = st.text_input(
          "Chapter Name (e.g., Sequence & Series, Chemical Bonding)"
      )
      c_subject = st.selectbox(
          "Subject", ["Physics", "Chemistry", "Mathematics"]
      )
      submitted = st.form_submit_button("Add Chapter")

      if submitted and c_name.strip():
        try:
          with conn.session as s:
            s.execute(
                "INSERT INTO chapters (chapter_name, subject) VALUES (:name,"
                " :subj) ON CONFLICT (chapter_name) DO NOTHING;",
                {"name": c_name.strip(), "subj": c_subject},
            )
            s.commit()
          st.success(f"Added chapter: {c_name.strip()}")
          st.rerun()
        except Exception as e:
          st.error(f"Error adding chapter: {e}")

    st.markdown("#### Existing Chapters")
    df_chapters = conn.query(
        "SELECT * FROM chapters ORDER BY chapter_id;", ttl=0
    )
    if not df_chapters.empty:
      st.dataframe(df_chapters, use_container_width=True)

      del_chapter = st.text_input("Enter exact Chapter Name to Delete")
      if st.button("Delete Chapter"):
        with conn.session as s:
          s.execute(
              "DELETE FROM chapters WHERE chapter_name = :name;",
              {"name": del_chapter},
          )
          s.execute(
              "DELETE FROM daily_practice_v2 WHERE chapter_name = :name;",
              {"name": del_chapter},
          )
          s.commit()
        st.warning(f"Deleted chapter: {del_chapter}")
        st.rerun()
    else:
      st.info("No chapters added yet. Add your chapters above first.")

  # --- TAB 2: DAILY QUESTION LOGGING ---
  with tab2:
    st.markdown("### Log Daily Questions Solved per Chapter")
    df_chapters_opt = conn.query(
        "SELECT chapter_name FROM chapters ORDER BY chapter_id;", ttl=0
    )
    chapter_options = (
        df_chapters_opt["chapter_name"].tolist()
        if not df_chapters_opt.empty
        else []
    )

    if chapter_options:
      with st.form("log_practice_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
          day_n = st.number_input("Day Number", min_value=1, max_value=45, value=1)
        with col2:
          context = st.text_input("Context / Date", value=f"Day {day_n}")
        with col3:
          selected_chap = st.selectbox("Chapter", chapter_options)
        with col4:
          q_count = st.number_input(
              "Questions Solved", min_value=0, step=1, value=10
          )

        log_submitted = st.form_submit_button("Save Daily Log Entry")
        if log_submitted:
          with conn.session as s:
            # Upsert query for PostgreSQL/Supabase
            s.execute(
                """
                            INSERT INTO daily_practice_v2 (day_num, date_or_context, chapter_name, questions_solved)
                            VALUES (:day, :ctx, :chap, :q)
                            ON CONFLICT (day_num, chapter_name) 
                            DO UPDATE SET questions_solved = daily_practice_v2.questions_solved + :q, date_or_context = :ctx;
                        """,
                {
                    "day": day_n,
                    "ctx": context,
                    "chap": selected_chap,
                    "q": q_count,
                },
            )
            s.commit()
          st.success(
              f"Logged {q_count} questions for {selected_chap} on Day {day_n}!"
          )
          st.rerun()

      st.markdown("#### All Logged Practice Records")
      df_logs = conn.query(
          "SELECT day_num AS Day, date_or_context AS Context, chapter_name AS Chapter, questions_solved AS \"Questions Solved\" FROM daily_practice_v2 ORDER BY day_num;",
          ttl=0,
      )
      if not df_logs.empty:
        st.dataframe(df_logs, use_container_width=True)
      else:
        st.info("No practice entries logged yet.")
    else:
      st.warning(
          "Please add chapters in the 'Chapters Manager' tab before logging"
          " questions!"
      )

  # --- TAB 3: OVERALL ANALYTICS ---
  with tab3:
    st.markdown("### 📈 Overall Performance & Chapter Breakdown")
    df_analytics = conn.query("SELECT * FROM daily_practice_v2;", ttl=0)

    if not df_analytics.empty:
      total_q = df_analytics["questions_solved"].sum()
      col1, col2 = st.columns(2)
      col1.metric("Total Questions / PYQs Solved Across All Days", int(total_q))

      st.markdown("---")
      st.markdown("#### 📚 Chapter-wise Question Accumulation")
      chapter_summary = (
          df_analytics.groupby("chapter_name")["questions_solved"]
          .sum()
          .reset_index()
      )
      chapter_summary.columns = [
          "Chapter Name",
          "Total Questions Solved (All Days Combined)",
      ]
      st.dataframe(chapter_summary, use_container_width=True)
    else:
      st.info("Log some question entries to view your analytics summary.")


if __name__ == "__main__":
  main()