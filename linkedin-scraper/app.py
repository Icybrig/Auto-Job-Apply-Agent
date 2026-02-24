import streamlit as st
import subprocess
import os


# Streamlit form for inputs
st.title('LinkedIn Job Scraper')

with st.form('scraper_form'):
    title = st.text_input('Job Title', value='backend developer')
    location = st.text_input('Job Location', value='newyork')
    data_name = st.text_input('Output File Name', value='backend_job')

    submit_button = st.form_submit_button('Run Scraper')


if submit_button:

    # Run the scraping script with the form inputs
    command = f'poetry run python -m linkedin-scraper --title "{title}" --data_name "{data_name}"'

    with st.spinner('Crawling in progress...'):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.stdout:
            st.write('Script Output:')
            st.text(result.stdout)

        if result.returncode == 0:
            st.success(f'Data successfully saved in {data_name}.csv')

            # The scraper writes the CSV next to main.py
            csv_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'linkedin-scraper',
                f'{data_name}.csv',
            )
            if os.path.exists(csv_path):
                with open(csv_path, 'rb') as f:
                    st.download_button(
                        label='Download CSV',
                        data=f,
                        file_name=f'{data_name}.csv',
                        mime='text/csv',
                    )
        else:
            st.error('Scraper failed.')
            if result.stderr:
                st.code(result.stderr, language='text')
    
   