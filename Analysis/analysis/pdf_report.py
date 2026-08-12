import os
from datetime import datetime

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image
)


def generate_pdf_report(
    results,
    output_folder,
    qc_settings
):
    """
    Generate one PDF report containing:

    Page 1:
        - Report information
        - QC settings
        - Explanation of QC measures

    Page 2:
        - Master Results

    Remaining pages:
        - One page per participant
        - Participant information
        - SJ / TOJ / SRT numerical results
        - Available participant plots
    """

    # ==================================================
    # PDF SETUP
    # ==================================================

    pdf_path = os.path.join(
        output_folder,
        "MSI_Analysis_Report.pdf"
    )

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(letter),
        rightMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch
    )

    styles = getSampleStyleSheet()

    # -------------------------
    # Master Results headings
    # -------------------------

    master_section_style = styles["Heading3"].clone(
        "MasterSection"
    )

    master_section_style.fontSize = 11
    master_section_style.leading = 13
    master_section_style.spaceAfter = 4

    # -------------------------
    # Plot headings
    # -------------------------

    plot_title_style = styles["Heading4"].clone(
        "PlotTitle"
    )

    plot_title_style.fontSize = 8
    plot_title_style.leading = 9
    plot_title_style.spaceAfter = 1

    # -------------------------
    # Small table text
    # -------------------------

    small_text_style = styles["Normal"].clone(
        "SmallTableText"
    )

    small_text_style.fontSize = 7
    small_text_style.leading = 8.5

    story = []

    # ==================================================
    # PAGE 1
    # REPORT INFORMATION
    # ==================================================

    story.append(
        Paragraph(
            "MSI Analysis Report",
            styles["Title"]
        )
    )

    story.append(
        Spacer(
            1,
            0.08 * inch
        )
    )

    report_date = datetime.now().strftime(
        "%B %d, %Y at %I:%M %p"
    )

    story.append(
        Paragraph(
            f"Generated: {report_date}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"Participants analyzed: {len(results)}",
            styles["Normal"]
        )
    )

    story.append(
        Spacer(
            1,
            0.12 * inch
        )
    )

    story.append(
        Paragraph(
            "Quality Control Overview",
            styles["Heading2"]
        )
    )

    # ==================================================
    # PAGE 1 LEFT SIDE
    # QC SETTINGS
    # ==================================================

    qc_data = [
        [
            "Setting",
            "Value"
        ],

        [
            "Minimum R²",
            f"{qc_settings['min_r2']:.2f}"
        ],

        [
            "Minimum response proportion",
            (
                f"{qc_settings['min_response_proportion']:.2f}"
            )
        ],

        [
            "Maximum response proportion",
            (
                f"{qc_settings['max_response_proportion']:.2f}"
            )
        ],

        [
            "Maximum SJ sigma",
            (
                f"{qc_settings['max_sigma_ms']} ms"
            )
        ],

        [
            "Maximum TOJ slope",
            (
                f"{qc_settings['max_slope_ms']} ms"
            )
        ],

        [
            "SJ / TOJ catch-trial criterion",
            "At least 8 / 10 correct"
        ],

        [
            "Anticipation threshold",
            (
                f"{qc_settings['min_rt_ms']} ms"
            )
        ],

        [
            "Minimum valid SRT trials",
            str(
                qc_settings[
                    "min_valid_srt_trials"
                ]
            )
        ],

        [
            "Maximum anticipations",
            str(
                qc_settings[
                    "max_anticipations"
                ]
            )
        ],

        [
            "Minimum mean RT",
            (
                f"{qc_settings['min_mean_rt_sec']:.2f} sec"
            )
        ],

        [
            "Maximum mean RT",
            (
                f"{qc_settings['max_mean_rt_sec']:.2f} sec"
            )
        ],
    ]

    qc_table = Table(
        qc_data,
        colWidths=[
            3.0 * inch,
            1.5 * inch
        ]
    )

    qc_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                4
            ),
        ])
    )

    # ==================================================
    # PAGE 1 RIGHT SIDE
    # QC EXPLANATIONS
    # ==================================================

    qc_explanation_data = [
        [
            "QC Measure",
            "What is it asking?"
        ],

        [
            "SJ Fit QC",
            (
                "Does the Gaussian adequately describe the observed "
                "SJ data? R² must meet the minimum criterion, and "
                "sigma must be positive and below the maximum."
            )
        ],

        [
            "TOJ Fit QC",
            (
                "Does the logistic function adequately describe the "
                "observed TOJ data? R² must meet the minimum criterion, "
                "and slope must be positive and below the maximum."
            )
        ],

        [
            "Response Range",
            (
                "Did the participant use both response options during "
                "the SJ or TOJ task?"
            )
        ],

        [
            "Response Bias",
            (
                "Did the participant avoid extremely one-sided "
                "responding outside the allowed response proportions?"
            )
        ],

        [
            "Catch Trials",
            (
                "Did the participant correctly identify at least 8 of the "
                "10 easy 1000-ms catch trials in each SJ and TOJ task? "
                "Catch trials are used as an attention/task-comprehension "
                "quality check and are excluded from psychometric fitting."
            )
        ],

        [
            "SRT Anticipation",
            (
                "Was a response so fast that it should be treated as "
                "anticipatory rather than a valid reaction?"
            )
        ],

        [
            "Valid SRT Trials",
            (
                "Were enough trials with a recorded Adjusted_RT "
                "available to support the SRT summary?"
            )
        ],

        [
            "Max. Anticipations",
            (
                "Did the participant stay within the maximum allowed "
                "number of anticipatory responses?"
            )
        ],

        [
            "Mean SRT Range",
            (
                "Was the participant's mean adjusted reaction time "
                "within the specified acceptable range?"
            )
        ],

        [
            "Overall QC",
            (
                "Did the participant pass all applicable QC checks? "
                "REVIEW means that at least one applicable criterion "
                "was not met and should be inspected."
            )
        ],
    ]

    # Convert explanation text to Paragraphs so it wraps
    for row_index in range(
        len(qc_explanation_data)
    ):

        for column_index in range(
            len(
                qc_explanation_data[
                    row_index
                ]
            )
        ):

            qc_explanation_data[
                row_index
            ][
                column_index
            ] = Paragraph(
                str(
                    qc_explanation_data[
                        row_index
                    ][
                        column_index
                    ]
                ),
                small_text_style
            )

    qc_explanation_table = Table(
        qc_explanation_data,
        colWidths=[
            1.35 * inch,
            3.65 * inch
        ]
    )

    qc_explanation_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "FONTNAME",
                (0, 1),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                3
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                3
            ),
        ])
    )

    # ==================================================
    # PAGE 1 TWO-COLUMN LAYOUT
    # ==================================================

    settings_heading = Paragraph(
        "QC Settings Used",
        styles["Heading3"]
    )

    explanation_heading = Paragraph(
        "What Are the QC Measures Asking?",
        styles["Heading3"]
    )

    qc_overview = Table(
        [
            [
                settings_heading,
                explanation_heading
            ],

            [
                qc_table,
                qc_explanation_table
            ]
        ],

        colWidths=[
            4.8 * inch,
            5.2 * inch
        ]
    )

    qc_overview.setStyle(
        TableStyle([

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2
            ),
        ])
    )

    story.append(
        qc_overview
    )

    # Page 2
    story.append(
        PageBreak()
    )

    # ==================================================
    # PAGE 2
    # MASTER RESULTS
    # ==================================================

    story.append(
        Paragraph(
            "Master Results",
            styles["Heading1"]
        )
    )

    story.append(
        Spacer(
            1,
            0.08 * inch
        )
    )

    # ==================================================
    # MASTER RESULTS HELPER
    # ==================================================

    def create_results_table(
        title,
        columns,
        display_names
    ):

        available_columns = [
            column
            for column in columns
            if column in results.columns
        ]

        if not available_columns:

            return Spacer(
                1,
                0
            )

        title_paragraph = Paragraph(
            title,
            master_section_style
        )

        table_data = [[
            display_names.get(
                column,
                column
            )
            for column in available_columns
        ]]

        for _, row in results.iterrows():

            table_row = []

            for column in available_columns:

                value = row[column]

                # -------------------------
                # QC values
                # -------------------------

                if column.endswith("_OK"):

                    if pd.isna(value):

                        value = "N/A"

                    else:

                        value = (
                            "PASS"
                            if bool(value)
                            else "REVIEW"
                        )

                # -------------------------
                # Floating point values
                # -------------------------

                elif isinstance(
                    value,
                    float
                ):

                    if pd.isna(value):

                        value = "N/A"

                    else:

                        value = (
                            f"{value:.2f}"
                        )

                else:

                    value = str(value)

                table_row.append(
                    value
                )

            table_data.append(
                table_row
            )

        table = Table(
            table_data,
            repeatRows=1
        )

        table.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    colors.grey
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4
                ),
            ])
        )

        container = Table(
            [
                [
                    title_paragraph
                ],

                [
                    table
                ]
            ]
        )

        container.setStyle(
            TableStyle([

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2
                ),
            ])
        )

        return container

    # ==================================================
    # PARTICIPANT SUMMARY MASTER TABLE
    # ==================================================

    participant_table = create_results_table(
        "Participant Summary",

        [
            "Participant_ID",
            "Age",
            "Gender",
            "Site",
            "Participant_OK"
        ],

        {
            "Participant_ID":
                "ID",

            "Participant_OK":
                "Overall QC"
        }
    )

    # ==================================================
    # SJ MASTER TABLE
    # ==================================================

    sj_table = create_results_table(
        "Simultaneity Judgment (SJ)",

        [
            "Participant_ID",
            "SJ_PSS_ms",
            "SJ_Sigma_ms",
            "SJ_TBW_ms",
            "SJ_R2",
            "SJ_Catch_Correct",
            "SJ_Catch_OK",
            "SJ_Fit_OK",
            "SJ_Response_Range_OK",
            "SJ_Response_Bias_OK"
        ],

        {
            "Participant_ID":
                "ID",

            "SJ_PSS_ms":
                "PSS",

            "SJ_Sigma_ms":
                "Sigma",

            "SJ_TBW_ms":
                "TBW",

            "SJ_R2":
                "R²",

            "SJ_Fit_OK":
                "Fit",

            "SJ_Response_Range_OK":
                "Range",

            "SJ_Response_Bias_OK":
                "Bias",

            "SJ_Catch_Correct":
                "Catch /10",

            "SJ_Catch_OK":
                "Catch QC",
        }
    )

    # ==================================================
    # TOJ MASTER TABLE
    # ==================================================

    toj_table = create_results_table(
        "Temporal Order Judgment (TOJ)",

        [
            "Participant_ID",
            "TOJ_PSS_ms",
            "TOJ_Slope",
            "TOJ_JND_ms",
            "TOJ_R2",
            "TOJ_Catch_Correct",
            "TOJ_Catch_OK",
            "TOJ_Fit_OK",
            "TOJ_Response_Range_OK",
            "TOJ_Response_Bias_OK"
        ],

        {
            "Participant_ID":
                "ID",

            "TOJ_PSS_ms":
                "PSS",

            "TOJ_Slope":
                "Slope",

            "TOJ_JND_ms":
                "JND",

            "TOJ_R2":
                "R²",

            "TOJ_Fit_OK":
                "Fit",

            "TOJ_Response_Range_OK":
                "Range",

            "TOJ_Response_Bias_OK":
                "Bias",

            "TOJ_Catch_Correct":
                "Catch /10",

            "TOJ_Catch_OK":
                "Catch QC",
        }
    )

    # ==================================================
    # SRT MASTER TABLE
    # ==================================================

    srt_table = create_results_table(
        "Simple Reaction Time (SRT)",

        [
            "Participant_ID",
            "SRT_Valid_Trials",
            "SRT_Misses",
            "SRT_Anticipations",
            "Mean_Adjusted_RT_ms",
            "Median_Adjusted_RT_ms",
            "SD_Adjusted_RT_ms",
            "CV_Adjusted_RT",
            "SRT_QC_OK"
        ],

        {
            "Participant_ID":
                "ID",

            "SRT_Valid_Trials":
                "Valid",

            "SRT_Misses":
                "Miss",

            "SRT_Anticipations":
                "Ant.",

            "Mean_Adjusted_RT_ms":
                "Mean",

            "Median_Adjusted_RT_ms":
                "Median",

            "SD_Adjusted_RT_ms":
                "SD",

            "CV_Adjusted_RT":
                "CV",

            "SRT_QC_OK":
                "QC"
        }
    )

    # ==================================================
    # ARRANGE MASTER RESULTS ON ONE PAGE
    # ==================================================

    master_grid = Table(
        [
            [
                participant_table,
                sj_table
            ],

            [
                toj_table,
                srt_table
            ]
        ],

        colWidths=[
            4.9 * inch,
            5.1 * inch
        ]
    )

    master_grid.setStyle(
        TableStyle([

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                4
            ),
        ])
    )

    story.append(
        master_grid
    )

    # Participant pages start next
    story.append(
        PageBreak()
    )

    # ==================================================
    # PARTICIPANT REPORT HELPERS
    # ==================================================

    def format_value(
        row,
        column,
        decimals=2,
        suffix=""
    ):

        if column not in row.index:

            return "N/A"

        value = row[column]

        if pd.isna(value):

            return "N/A"

        try:

            return (
                f"{float(value):.{decimals}f}"
                f"{suffix}"
            )

        except (
            ValueError,
            TypeError
        ):

            return str(value)

    def qc_status(
        row,
        column
    ):

        if column not in row.index:

            return "N/A"

        value = row[column]

        if pd.isna(value):

            return "N/A"

        return (
            "PASS"
            if bool(value)
            else "REVIEW"
        )

    # ==================================================
    # INDIVIDUAL PARTICIPANT REPORTS
    # ==================================================

    for participant_index, (_, row) in enumerate(
        results.iterrows()
    ):

        participant_id = row.get(
            "Participant_ID",
            "Unknown"
        )

        source_file = row.get(
            "Source_File",
            ""
        )

        participant_folder = os.path.join(
            output_folder,
            str(source_file)
        )

        # ==================================================
        # PARTICIPANT HEADING
        # ==================================================

        story.append(
            Paragraph(
                f"Participant {participant_id}",
                styles["Heading1"]
            )
        )

        participant_info = (
            f"<b>Age:</b> "
            f"{row.get('Age', 'N/A')}"
            f"&nbsp;&nbsp;&nbsp;&nbsp;"

            f"<b>Gender:</b> "
            f"{row.get('Gender', 'N/A')}"
            f"&nbsp;&nbsp;&nbsp;&nbsp;"

            f"<b>Site:</b> "
            f"{row.get('Site', 'N/A')}"
            f"&nbsp;&nbsp;&nbsp;&nbsp;"

            f"<b>Overall QC:</b> "
            f"{qc_status(row, 'Participant_OK')}"
        )

        story.append(
            Paragraph(
                participant_info,
                styles["Normal"]
            )
        )

        story.append(
            Spacer(
                1,
                0.08 * inch
            )
        )

        # ==================================================
        # PARTICIPANT RESULTS TABLE
        # ==================================================

        participant_results_data = [
            [
                "Task",
                "Measure 1",
                "Measure 2",
                "Measure 3",
                "R² / CV",
                "Catch",
                "Fit QC"
            ]
        ]

        # -------------------------
        # SJ
        # -------------------------

        if "SJ_PSS_ms" in results.columns:

            participant_results_data.append([
                "SJ",

                (
                    "PSS: "
                    + format_value(
                        row,
                        "SJ_PSS_ms",
                        suffix=" ms"
                    )
                ),

                (
                    "Sigma: "
                    + format_value(
                        row,
                        "SJ_Sigma_ms",
                        suffix=" ms"
                    )
                ),

                (
                    "TBW: "
                    + format_value(
                        row,
                        "SJ_TBW_ms",
                        suffix=" ms"
                    )
                ),

                (
                    "R²: "
                    + format_value(
                        row,
                        "SJ_R2",
                        decimals=3
                    )
                ),
                (
                        format_value(
                            row,
                            "SJ_Catch_Correct",
                            decimals=0
                        )
                        + "/10 "
                        + qc_status(
                    row,
                    "SJ_Catch_OK"
                )
                ),

                qc_status(
                    row,
                    "SJ_Fit_OK"
                )
            ])

        # -------------------------
        # TOJ
        # -------------------------

        if "TOJ_PSS_ms" in results.columns:

            participant_results_data.append([
                "TOJ",

                (
                    "PSS: "
                    + format_value(
                        row,
                        "TOJ_PSS_ms",
                        suffix=" ms"
                    )
                ),

                (
                    "Slope: "
                    + format_value(
                        row,
                        "TOJ_Slope"
                    )
                ),

                (
                    "JND: "
                    + format_value(
                        row,
                        "TOJ_JND_ms",
                        suffix=" ms"
                    )
                ),

                (
                    "R²: "
                    + format_value(
                        row,
                        "TOJ_R2",
                        decimals=3
                    )
                ),
                (
                        format_value(
                            row,
                            "TOJ_Catch_Correct",
                            decimals=0
                        )
                        + "/10 "
                        + qc_status(
                    row,
                    "TOJ_Catch_OK"
                )
                ),

                qc_status(
                    row,
                    "TOJ_Fit_OK"
                )
            ])

        # -------------------------
        # SRT
        # -------------------------

        if "Mean_Adjusted_RT_ms" in results.columns:

            participant_results_data.append([
                "SRT",

                (
                    "Mean: "
                    + format_value(
                        row,
                        "Mean_Adjusted_RT_ms",
                        suffix=" ms"
                    )
                ),

                (
                    "Median: "
                    + format_value(
                        row,
                        "Median_Adjusted_RT_ms",
                        suffix=" ms"
                    )
                ),

                (
                    "SD: "
                    + format_value(
                        row,
                        "SD_Adjusted_RT_ms",
                        suffix=" ms"
                    )
                ),

                (
                    "CV: "
                    + format_value(
                        row,
                        "CV_Adjusted_RT",
                        decimals=3
                    )
                ),

                qc_status(
                    row,
                    "SRT_QC_OK"
                )
            ])

        participant_results_table = Table(
            participant_results_data,

            colWidths=[
                0.50 * inch,  # Task
                1.55 * inch,  # Measure 1
                1.55 * inch,  # Measure 2
                1.55 * inch,  # Measure 3
                1.10 * inch,  # R2 / CV
                1.20 * inch,  # Catch
                0.75 * inch  # QC
            ]
        )

        participant_results_table.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "FONTNAME",
                    (0, 1),
                    (0, -1),
                    "Helvetica-Bold"
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.grey
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4
                ),
            ])
        )

        story.append(
            participant_results_table
        )

        story.append(
            Spacer(
                1,
                0.06 * inch
            )
        )

        # ==================================================
        # PARTICIPANT PLOTS
        # ==================================================

        plot_specs = [
            (
                "SJ_Raw.png",
                "SJ Raw"
            ),

            (
                "SJ_Fitted.png",
                "SJ Fitted"
            ),

            (
                "SRT_Histogram.png",
                "SRT Histogram"
            ),

            (
                "TOJ_Raw.png",
                "TOJ Raw"
            ),

            (
                "TOJ_Fitted.png",
                "TOJ Fitted"
            )
        ]

        plot_items = []

        # -------------------------
        # Load plots
        # -------------------------

        for filename, plot_title in plot_specs:

            plot_path = os.path.join(
                participant_folder,
                filename
            )

            if not os.path.exists(
                plot_path
            ):

                continue

            plot_image = Image(
                plot_path,
                width=2.8 * inch,
                height=1.75 * inch
            )

            plot_container = Table(
                [
                    [
                        Paragraph(
                            plot_title,
                            plot_title_style
                        )
                    ],

                    [
                        plot_image
                    ]
                ]
            )

            plot_container.setStyle(
                TableStyle([

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP"
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        2
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        2
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        1
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        1
                    ),
                ])
            )

            plot_items.append(
                plot_container
            )

        # ==================================================
        # ARRANGE PLOTS
        # ==================================================

        plot_rows = []

        if plot_items:

            # First row:
            # SJ Raw / SJ Fitted / SRT
            first_row = plot_items[:3]

            while len(first_row) < 3:

                first_row.append(
                    Spacer(
                        1,
                        0
                    )
                )

            plot_rows.append(
                first_row
            )

            # Second row:
            # TOJ Raw / TOJ Fitted
            remaining = plot_items[3:]

            if remaining:

                while len(remaining) < 3:

                    remaining.append(
                        Spacer(
                            1,
                            0
                        )
                    )

                plot_rows.append(
                    remaining
                )

        if plot_rows:

            plot_grid = Table(
                plot_rows,

                colWidths=[
                    3.15 * inch,
                    3.15 * inch,
                    3.15 * inch
                ]
            )

            plot_grid.setStyle(
                TableStyle([

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP"
                    ),

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        2
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        2
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        2
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        2
                    ),
                ])
            )

            story.append(
                plot_grid
            )

        # ==================================================
        # PAGE BREAK BETWEEN PARTICIPANTS
        # ==================================================

        if (
            participant_index
            < len(results) - 1
        ):

            story.append(
                PageBreak()
            )

    # ==================================================
    # BUILD PDF
    # ==================================================

    doc.build(
        story
    )

    return pdf_path