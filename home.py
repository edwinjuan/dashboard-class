import streamlit as st
import pandas as pd
import requests
import numpy as np
import streamlit_authenticator as stauth
import altair as alt
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
import plotly.graph_objects as go

st.set_page_config(layout="wide")
# Hide setting menu
# hide_menu = """
# <style>
# #MainMenu {
#     visibility:hidden;
# }
# footer{
#     visibility:hidden;
# }
# </style>
# """

if 'token' not in st.session_state:
    st.session_state['token'] = None

def main():
     # ---- Preparing data Streamlit Login ---- 
    baseURL = 'http://127.0.0.1:8000/api'
    #st.markdown(hide_menu, unsafe_allow_html=True)
    # users = database_func.get_all_user()
    response = requests.get(baseURL + '/users')

    credentials = {"usernames": {}}
    for data in response.json()['data']:
        user_dict = {"name": data['users_id'], "password": data['password']}
        credentials['usernames'].update({data['email']: user_dict})

    # id akan masuk ke st.session_state['name']
    authenticator = stauth.Authenticate(credentials, 'class_dashboard', 'abcde', cookie_expiry_days=7)
    
    name, authentication_status, username = authenticator.login("Login", "main")

    if authentication_status == False:
        st.error('Username/password is incorrect')
    elif authentication_status == None:
        st.warning('Please enter your username and password')
    elif authentication_status:
        col1, col2 = st.columns([8, 2])
        with col1:
            st.header("Performance Class Dashboard")
        with col2:
            st.markdown('###')
            authenticator.logout('Logout', 'main') 
        # Filter kelas
        response = requests.get(baseURL + '/class/st/show/' + str(st.session_state['name']))
        optionsClass = {}
        for data in response.json()['data']:
            key = data['code'] + ' - ' + data['matkul_name'] + ' - ' + data['class_order']
            value = data['class_id']
            optionsClass[key] = value
        selected_class = st.selectbox('Class: ', options=list(optionsClass.keys())) 
        # Get the selected value from the dictionary
        selected_class_id = optionsClass[selected_class]

        # Get Data Dashboard Class
        response = requests.get(baseURL + '/class/dashboard/' + str(selected_class_id))
        responseAsgn = requests.get(baseURL + '/class/dashboard/asgn/' + str(selected_class_id))
        responseCpmk = requests.get(baseURL + '/class/dashboard/matkul/' + str(selected_class_id))

        if (response.status_code == 200):
            # --- Get and preparing All Data ---
            df = pd.DataFrame(response.json()['data'])
            df_asign = pd.DataFrame(responseAsgn.json()['data'])
            df_cpmk = pd.DataFrame(responseCpmk.json()['data'])
            # delete unused column on cpmk dataframe and assignment dataframe
            df_cpmk = df_cpmk.drop(columns=['created_at', 'updated_at', 'matkul_id'])
            df_asign = df_asign.drop(columns=['cpmk_id', 'cpmk_description', 'percentage'])
            # change datatype to numeric
            df['grade'] = pd.to_numeric(df['grade'])
            df['percentage'] = pd.to_numeric(df['percentage'])
            df_cpmk['percentage'] = pd.to_numeric(df_cpmk['percentage'])
            # Change string list into list of number on cpmk_list and cpmk_grade
            def changeListStringToListInt(x):
                listOfString = x[1:-1].split(',')
                listOfInt = [eval(i) for i in listOfString]
                return listOfInt
            df_asign['cpmk_list'] = df_asign['cpmk_list'].apply(changeListStringToListInt)
            df['cpmk_grade'] = df['cpmk_grade'].apply(changeListStringToListInt)
            df['assignment_cpmk_list'] = df['assignment_cpmk_list'].apply(changeListStringToListInt)
            
            #Nanti dihapus
            # st.dataframe(df)
            #st.dataframe(df_asign)
            #st.dataframe(df_cpmk)

            # --- Calculate all current student cpmk store ---
            # Get dataframe of current total grade
            df_total = df.copy()
            # extract data array to row
            list_cpmk_col = []
            for idx, row in df_total.iterrows():
                cpmk_list = row['assignment_cpmk_list']
                cpmk_grade = row['cpmk_grade']
                for i, cpmk_val in enumerate(cpmk_list):
                    df_total.loc[idx, str(cpmk_val)] = cpmk_grade[i]
                    list_cpmk_col.append(str(cpmk_val))
            list_cpmk_col = list(dict.fromkeys(list_cpmk_col))
            # calculate sum and count
            df_total_grouped_sum = df_total.groupby(['npm', 'name'])[list_cpmk_col].sum().reset_index()
            df_total_grouped_count = df_total.groupby(['npm', 'name'])[list_cpmk_col].count().reset_index()
            # calculate the final average grade each cpmk
            for col in list_cpmk_col:
                colTotName = "average {}".format(col)
                colCountName = "count {}".format(col)
                df_total_grouped_sum[colCountName] = df_total_grouped_count[col]
                df_total_grouped_sum[colTotName] = df_total_grouped_sum[col] / df_total_grouped_count[col]
                # calculate final weighted grade
                colWeightName = "weighted {}".format(col)
                percent = df_cpmk[df_cpmk['cpmk_id'] == int(col)]['percentage'].values[0]
                df_total_grouped_sum[colWeightName] = df_total_grouped_sum[colTotName] * (percent/100)            
            # calculate final grade
            for i, row in df_total_grouped_sum.iterrows():
                total = 0
                for cpmk in list_cpmk_col:
                    colName = "weighted {}".format(cpmk)
                    total = total + row[colName]
                df_total_grouped_sum.loc[i, "final"] = total
            # sort data
            df_grade_total = df_total_grouped_sum.sort_values(by=['final'], ascending=False)



            # --- Show header metrics ---
            col1, col2, col3, col4, col5 = st.columns(5)
            # Number of Students
            df_students_distinct = df.drop_duplicates(subset="npm")
            col1.markdown(
                f"""
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
                <div style="
                    background-color: #262730;
                    box-shadow: 0px 3px 5px rgba(0, 0, 0, 0.2);
                    padding: 10px;
                    border-radius: 5px;
                    display: flex;
                    align-items: center;
                ">
                    <div style="flex-basis: 33.33%; margin-left: 20px">
                        <i class="fa-solid fa-user-group" style="font-size: 50px; color: #68ee97"></i>
                    </div>
                    <div style="flex-basis: 66.67%; margin-left: 20px"">
                        <h3 style="text-align: left; color: white; font-size: 20px;  margin-top: 0px;">Students</h3>
                        <h3 style="text-align: left; color: white; font-size: 50px;  margin-top: -20px; margin-bottom: 0px;">{df_grade_total.shape[0]}</h3>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Average of total grade
            strAvgGrade = "%.2f" % df_grade_total['final'].mean()
            col2.markdown(
                f"""
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
                <div style="
                    background-color: #262730;
                    box-shadow: 0px 3px 5px rgba(0, 0, 0, 0.2);
                    padding: 10px;
                    border-radius: 5px;
                    display: flex;
                    align-items: center;
                ">
                    <div style="flex-basis: 33.33%; margin-left: 20px">
                        <i class="fa-solid fa-chalkboard-user" style="font-size: 50px; color: #68ee97"></i>
                    </div>
                    <div style="flex-basis: 66.67%; margin-left: 20px"">
                        <h3 style="text-align: left; color: white; font-size: 20px;  margin-top: 0px;">Average Grade</h3>
                        <h3 style="text-align: left; color: white; font-size: 50px;  margin-top: -20px; margin-bottom: 0px;">{strAvgGrade}</h3>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Assignment Done
            current_assign = df['assignment_id'].drop_duplicates().shape[0]
            tot_assign = df_asign['assignment_id'].shape[0]
            assign_percent = (current_assign / tot_assign) * 100
            col3.markdown(
                f"""
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
                <div style="
                    background-color: #262730;
                    box-shadow: 0px 3px 5px rgba(0, 0, 0, 0.2);
                    padding: 10px;
                    border-radius: 5px;
                    display: flex;
                    align-items: center;
                ">
                    <div style="flex-basis: 33.33%; margin-left: 20px">
                        <i class="fa-solid fa-list-check" style="font-size: 50px; color: #68ee97"></i>
                    </div>
                    <div style="flex-basis: 66.67%; margin-left: 20px"">
                        <h3 style="text-align: left; color: white; font-size: 20px;  margin-top: 0px;">Assignment Done</h3>
                        <h3 style="text-align: left; color: white; font-size: 50px;  margin-top: -20px; margin-bottom: 0px;">{assign_percent}%</h3>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Total Score tertinggi
            best_grade = "%.2f" % df_grade_total['final'].iloc[0]
            col4.markdown(
                f"""
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
                <div style="
                    background-color: #262730;
                    box-shadow: 0px 3px 5px rgba(0, 0, 0, 0.2);
                    padding: 10px;
                    border-radius: 5px;
                    display: flex;
                    align-items: center;
                ">
                    <div style="flex-basis: 33.33%; margin-left: 20px">
                        <i class="fa-solid fa-trophy" style="font-size: 50px; color: #68ee97"></i>
                    </div>
                    <div style="flex-basis: 66.67%; margin-left: 20px"">
                        <h3 style="text-align: left; color: white; font-size: 20px;  margin-top: 0px;">Best Grade</h3>
                        <h3 style="text-align: left; color: white; font-size: 50px;  margin-top: -20px; margin-bottom: 0px;">{best_grade}</h3>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Total score terendah
            worst_grade = "%.2f" % df_grade_total['final'].iloc[-1]
            col5.markdown( 
                f"""
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
                <div style="
                    background-color: #262730;
                    box-shadow: 0px 3px 5px rgba(0, 0, 0, 0.2);
                    padding: 10px;
                    border-radius: 5px;
                    display: flex;
                    align-items: center;
                ">
                    <div style="flex-basis: 33.33%; margin-left: 20px">
                        <i class="fa-solid fa-person-drowning" style="font-size: 50px; color: #68ee97"></i>
                    </div>
                    <div style="flex-basis: 66.67%; margin-left: 20px"">
                        <h3 style="text-align: left; color: white; font-size: 20px;  margin-top: 0px;">Worst Grade</h3>
                        <h3 style="text-align: left; color: white; font-size: 50px;  margin-top: -20px; margin-bottom: 0px;">{worst_grade}</h3>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            st.markdown('###') # Separator
            
            # Set Column
            st.subheader('Average CPMK Grade')
            cols = st.columns(df_cpmk.shape[0])
            col1, col2 = st.columns([3,2])
            col3, col4 = st.columns([3,2])
            

            # --- Bar chart to see students grade compare to average every assignment ---
            col1.subheader('Grade Assignment Compare to Average')
            selected_assignment = col1.selectbox('Assignment: ', options=list(df_asign['assignment_description']))
            #data processing
            data = df[df['assignment_description'] == selected_assignment]
            avg_grade = data["grade"].mean()
            data["Above Average"] = data["grade"].apply(lambda x: 'Yes' if x > avg_grade else 'No')
            #charting
            chart2 = alt.Chart(data, height=500).mark_bar().encode(
                x=alt.X("npm", sort=None),
                y=alt.Y('grade', axis=alt.Axis(title='Grade')),
                color=alt.Color("Above Average:N", scale=alt.Scale(domain=['Yes', 'No'], range=["green", "red"])),
                tooltip=["name", "grade", "Above Average"]
            ).properties(
                title=f"(Average Grade = {avg_grade:.2f})"
            )
            #Add threshold line
            threshold_line = alt.Chart(pd.DataFrame({"Avg": [avg_grade]})).mark_rule().encode(
                y="Avg:Q"
            )
            col1.altair_chart(chart2 + threshold_line, use_container_width=True, theme='streamlit')


            # --- Stacked Barchart for students grade ---
            filtered_columns = df_grade_total.filter(regex=f'^(weighted)')
            # Include additional columns
            selected_columns = pd.concat([df_grade_total[['npm', 'name']], filtered_columns], axis=1)
            df_melted = selected_columns.melt(id_vars=['npm', 'name'], var_name='weighted', value_name='Weighted Grade')
            # Get top 10 NPM
            npm_top = df_grade_total.iloc[0:10]['npm']
            chart_data = df_melted[df_melted['npm'].isin(npm_top)]
            # Put CPMK Number on cpmk dataframe
            for i, row in df_cpmk.iterrows():
                df_cpmk.loc[i, 'number'] = "CPMK {}".format(int(i+1))
            # Put CPMK into chart_data
            def putCPMK(data):
                listStr = data.split(' ')
                cpmkStr = df_cpmk[df_cpmk['cpmk_id'] == int(listStr[1])]['number'].values[0]
                return cpmkStr
            chart_data['cpmk'] = chart_data['weighted'].apply(putCPMK)
            # Put Real Grade into chart_data
            def putRealGrade(data):
                listStr = data['weighted'].split(' ')
                percent = df_cpmk[df_cpmk['cpmk_id'] == int(listStr[1])]['percentage'].values[0]
                realGrade = data['Weighted Grade'] * (100/percent)
                return realGrade
            chart_data['Grade'] = chart_data.apply(putRealGrade, axis=1)
            # Put current final grade into chart_data
            def putFinalGrade(data):
                finalGrade = df_grade_total[df_grade_total['npm'] == data['npm']]['final'].values[0]
                return finalGrade
            chart_data['Final Grade'] = chart_data.apply(putFinalGrade, axis=1)
            # Charting
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Weighted Grade:Q'),
                y=alt.Y('npm:N', sort='-x'),
                color=alt.Color('cpmk:N', legend=alt.Legend(
                    orient='top',
                    legendX=130, legendY=-40,
                    direction='horizontal',
                    title=None)),
                tooltip=["name", "npm", 'cpmk', 'Weighted Grade', 'Grade', 'Final Grade']
            ).properties(
                height=600,
                title='Top 10 Students Performance'
            )
            chart = chart.configure_title(
                fontSize=28  # Set the desired font size
            )
            col2.altair_chart(chart, use_container_width=True)

            # --- Performance Ratio ---
            # Clustering
            features = df_grade_total[['final']].values
            max_clusters = 8  # Maximum number of clusters to consider
            best_score = -1
            optimal_clusters = None
            # Check the most fit number of cluster
            for n_clusters in range(2, max_clusters+1):
                kmeans = KMeans(n_clusters=n_clusters, random_state=0)
                labels = kmeans.fit_predict(features)
                score = silhouette_score(features, labels)
                if score > best_score:
                    best_score = score
                    optimal_clusters = n_clusters
            # Perform K-means clustering with the optimal number of clusters
            kmeans = KMeans(n_clusters=optimal_clusters, random_state=0)
            labels = kmeans.fit_predict(features)
            # Add the cluster labels to the original DataFrame
            df_grade_total['Cluster'] = labels
            # Calculate the percentage of students in each cluster
            cluster_percentage = df_grade_total['Cluster'].value_counts(normalize=True).reset_index()
            cluster_percentage.columns = ['Cluster', 'Percentage']
            cluster_percentage['data'] = 'data'
            cluster_percentage['Percentage'] = cluster_percentage['Percentage'] * 100
            # Create a stacked bar chart to visualize the percentage of each student in each cluster
            chart = alt.Chart(cluster_percentage).mark_bar().encode(
                x='Percentage:Q',
                y='data',
                color=alt.Color('Cluster:N', legend=alt.Legend(
                    orient='top',
                    legendX=130, legendY=-40,
                    direction='horizontal',
                    title='Cluster')),
                tooltip=['Cluster', 'Percentage'],
                text=alt.Text('Percentage:Q', format='.1%')
            ).properties(
                title='Students Performance'
            ).configure_axisY(
                title=None,
                labels=False
            )
            chart = chart.configure_title(
                fontSize=28  # Set the desired font size
            )
            col4.altair_chart(chart, use_container_width=True)

            # --- scatter plot for cluster distribution ---
            # Change column name from final to grade
            df_grade_cluster = df_grade_total.rename(columns={'final': 'Grade'})
            # Define the color scale for the scatter plot
            # Get unique cluster values
            clusters = df_grade_cluster['Cluster'].unique().tolist()
            color_scale = alt.Scale(
                domain=clusters,
                range=['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#00fff7', '#ff00d0', '#ff9900', '#ff0077']  # Add more colors as needed
            )
            # Plotting Scatter plot
            parallel_plot = alt.Chart(df_grade_cluster).mark_circle(size=50).encode(
                x=alt.X('npm:O', axis=alt.Axis(labels=True)),
                color=alt.Color('Cluster:N', scale=color_scale),
                detail='Cluster:N',
                y=alt.Y(alt.repeat("column"), type='quantitative')
            ).properties(
                title='Students Cluster Pattern',
                width=490,
                height=400
            ).repeat(
                column=['Grade']
            ).interactive()
            parallel_plot = parallel_plot.configure_title(
                fontSize=28  # Set the desired font size
            )
            col4.altair_chart(parallel_plot, use_container_width=True)

            # --- Show remaining grade needed ---
            # if (int(df['percentage'].unique().sum()) < 100):
            #     col3.subheader('__Nilai minimum di sisah assignment untuk lulus__')
            #     data = df.copy()
            #     passing_grade = col3.number_input(value=60, label='Passing Grade:')
            #     # calculate current overall score for each student
            #     data['Total Score'] = (data['percentage'] / 100) * data['grade']
            #     grouped_data = data.groupby(['npm', 'name'])[['Total Score', 'percentage']].sum().reset_index()
            #     #get remaining assignment
            #     data_merge = pd.merge(df_asign, data, on="assignment_description", how='left').reset_index()
            #     data_merge = data_merge[data_merge['cpmk_id_y'].isna()]
            #     data_merge['percentage_x'] = pd.to_numeric(data_merge['percentage_x'])
            #     #calculate minimum grade for remaining assignment
            #     for i in range(data_merge.shape[0]):
            #         #title = data_merge.iloc[i]['assignment_description']
            #         grouped_data['Average Grade Needed'] = ((passing_grade - grouped_data['Total Score'])*(data_merge.iloc[i]['percentage_x']/data_merge['percentage_x'].sum())) / (data_merge.iloc[i]['percentage_x']/100)
            #     # Configure table Aggrid
            #     # Round up the decimal number
            #     numeric_cols = grouped_data.select_dtypes(include=['float64', 'int64']).columns
            #     grouped_data[numeric_cols] = grouped_data[numeric_cols].applymap("{:.2f}".format)
            #     grouped_data[numeric_cols] = grouped_data[numeric_cols].astype(float)
            #     # Apply function to dataframe and display as table
            #     col3.dataframe(grouped_data, use_container_width=True, height=400)

            # --- CPMK Performance per Assignment ---
            col3.subheader("CPMK Grade Distribution")
            # Get dataframe of current total grade
            df_total2 = df.copy()
            # extract data array to row
            list_cpmk_col2 = []
            for idx, row in df_total2.iterrows():
                cpmk_list = row['assignment_cpmk_list']
                cpmk_grade = row['cpmk_grade']
                for i, cpmk_val in enumerate(cpmk_list):
                    colName = "CPMK {}".format(cpmk_val)
                    df_total2.loc[idx, colName] = cpmk_grade[i]
                    list_cpmk_col2.append(colName)
            list_cpmk_col2 = list(dict.fromkeys(list_cpmk_col2))
            # get average cpmk grade for every assignment
            df_grouped_assign = df_total2.groupby(['assignment_id', 'assignment_description'])[list_cpmk_col2].mean().reset_index()
            # Melt the DataFrame to long format
            df_melted = df_grouped_assign.melt(id_vars=['assignment_id', 'assignment_description'], var_name='CPMK', value_name='Grade')
            df_melted.fillna(0, inplace=True)
            df_filtered = df_melted[df_melted['Grade'] != 0]
            # Calculate the average grade for each CPMK
            df_avg_grade = df_filtered.groupby('CPMK')['Grade'].mean().reset_index()
            df_avg_grade.sort_values(by=['CPMK'], inplace=True)
            # Create Altair Pie Chart
            # Create a list to store the charts
            charts = []
            # Define the number of charts per row
            charts_per_row = 2
            # Iterate over the assignments and create the charts
            CPMKNumber = 0  # give number to cpmk
            for i in range(0, len(df_avg_grade), charts_per_row):
                cpmk_subset = df_avg_grade.iloc[i:i + charts_per_row]
                cpmk_subset_filtered = df_filtered[df_filtered['CPMK'].isin(cpmk_subset['CPMK'])]
                # Create the pie charts for the current row
                row_charts = []
                for cpmk in cpmk_subset['CPMK']:
                    df_cpmk2 = cpmk_subset_filtered[cpmk_subset_filtered['CPMK'] == cpmk]
                    CPMKNumber = CPMKNumber + 1
                    # Create the pie chart
                    base = alt.Chart(df_cpmk2).encode(
                        alt.Color('assignment_description:N', legend=alt.Legend(title='Assignment', orient='top')),
                        theta=alt.Theta('Grade:Q', stack=True),
                        tooltip=['assignment_description', 'Grade']
                    ).properties(
                        title=f'CPMK {CPMKNumber}'
                    )
                    # Add text marks to show the numbers on each slice
                    pie = base.mark_arc(outerRadius=120)
                    text = base.mark_text(radius=145, size=14).encode(text="Grade:Q")
                    # add all chart
                    chart = (pie + text)
                    row_charts.append(chart)
                # Concatenate the charts horizontally for the current row
                row_chart = alt.hconcat(*row_charts)
                # Add the row chart to the list of charts
                charts.append(row_chart)
            # Concatenate the row charts vertically
            combined_chart = alt.vconcat(*charts)
            col3.write(combined_chart)


            # --- Show Progress CPMK ---
            # Preparing data
            df_data = df_cpmk.copy()
            df_data['average'] = 0
            avg_cpmk_list = {}
            for cpmk in list_cpmk_col:
                colName = "average {}".format(cpmk)
                avg = df_grade_total[colName].mean()
                df_data.loc[df_data['cpmk_id'] == int(cpmk), 'average'] = avg
            
            # Create a Gauge chart
            for i, column in enumerate(cols):
                #description = df_cpmk[df_cpmk['cpmk_id'] == data_cpmk.loc[i, 'cpmk_id']]['description'].item()
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = df_data.loc[i, 'average'],
                    title = {'text': f'CPMK {i+1}'},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "Green"},
                        'borderwidth': 2,
                    }
                ))
                fig.update_layout(height=300)
                # # Render the chart in Streamlit
                column.plotly_chart(fig, use_container_width=True)
                



        else:
            st.warning("Data is not found!")

    
    




if __name__ == '__main__':
    main()