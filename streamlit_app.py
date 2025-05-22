import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Rooster Impact Simulator", layout="wide")

st.title("Onderwijsrooster Simulatie bij Locatie-uitval")

st.markdown("""
Deze tool voert simulaties uit op het onderwijsrooster wanneer onderwijsruimtes of gebouwen niet langer beschikbaar zijn vanaf een bepaalde datum. Het vergelijkt benodigde groepsgroottes met capaciteit van beschikbare ruimtes en toont welke activiteiten niet meer geplaatst kunnen worden.
""")

# --- Uploads ---
st.header("1. Upload gegevens")

rooster_file = st.file_uploader("Upload roosterbestand (bijv. 'All Schedule activities')", type=["csv", "xlsx"])
locaties_file = st.file_uploader("Upload locatiebestand met capaciteiten (bijv. 'Dataset All locations and maximum group size')", type=["csv", "xlsx"])

if rooster_file and locaties_file:
    # Load files
    def read_file(f):
        if f.name.endswith(".csv"):
            return pd.read_csv(f)
        else:
            return pd.read_excel(f)

    rooster_df = read_file(rooster_file)
    locaties_df = read_file(locaties_file)

    # Normaliseer kolomnamen (voor uniformiteit)
    rooster_df.columns = rooster_df.columns.str.lower()
    locaties_df.columns = locaties_df.columns.str.lower()

    # --- Instellingen selectie ---
    st.header("2. Selecteer locaties/gebouwen die niet beschikbaar zijn")

    locaties_df['gebouw'] = locaties_df['ruimte'].str.extract(r'(^[A-Za-z]+)')  # Veronderstel dat 'ruimte' kolomnamen zoals 'A1.01' heeft
    unieke_gebouwen = sorted(locaties_df['gebouw'].dropna().unique())
    unieke_locaties = sorted(locaties_df['ruimte'].dropna().unique())

    geselecteerde_gebouwen = st.multiselect("Selecteer gebouwen die niet beschikbaar zijn", unieke_gebouwen)
    geselecteerde_locaties = st.multiselect("Of selecteer specifieke locaties", unieke_locaties)
    vanaf_datum = st.date_input("Vanaf welke datum zijn deze locaties niet beschikbaar?", datetime.today())

    # Combineer gekozen ruimtes
    ruimtes_te_verwijderen = set(locaties_df[locaties_df['gebouw'].isin(geselecteerde_gebouwen)]['ruimte']) | set(geselecteerde_locaties)

    # --- Simulatie ---
    st.header("3. Simuleer impact op rooster")

    if st.button("Voer simulatie uit"):
        rooster_df['startdatum'] = pd.to_datetime(rooster_df['startdatum'], errors='coerce')
        rooster_df['einddatum'] = pd.to_datetime(rooster_df['einddatum'], errors='coerce')

        # Filter activiteiten op datum en ruimte
        conflicten = rooster_df[
            (rooster_df['ruimte'].isin(ruimtes_te_verwijderen)) &
            (rooster_df['startdatum'] >= pd.to_datetime(vanaf_datum))
        ]

        # Controleer op capaciteit
        locaties_cap = locaties_df.set_index('ruimte')['capaciteit'].to_dict()
        rooster_df['capaciteit'] = rooster_df['ruimte'].map(locaties_cap)
        rooster_df['capaciteit'] = pd.to_numeric(rooster_df['capaciteit'], errors='coerce')
        rooster_df['groepgrootte'] = pd.to_numeric(rooster_df['groepgrootte'], errors='coerce')

        rooster_df['capaciteit_ok'] = rooster_df['groepgrootte'] <= rooster_df['capaciteit']

        # Markeer welke na uitval niet herplaatst kunnen worden
        beschikbare_locaties_na_datum = locaties_df[~locaties_df['ruimte'].isin(ruimtes_te_verwijderen)]

        herplaatsbare = []
        niet_herplaatsbaar = []

        for _, row in conflicten.iterrows():
            benodigde = row['groepgrootte']
            mogelijke = beschikbare_locaties_na_datum[beschikbare_locaties_na_datum['capaciteit'] >= benodigde]
            if mogelijke.empty:
                niet_herplaatsbaar.append(row)
            else:
                herplaatsbare.append(row)

        st.subheader("Resultaten simulatie")
        st.markdown(f"""
        - Totaal aantal getroffen activiteiten: **{len(conflicten)}**
        - Aantal activiteiten dat herplaatst kan worden: **{len(herplaatsbare)}**
        - Aantal activiteiten dat **niet** herplaatst kan worden: **{len(niet_herplaatsbaar)}**
        """)

        if niet_herplaatsbaar:
            st.subheader("Niet herplaatsbare activiteiten")
            niet_df = pd.DataFrame(niet_herplaatsbaar)
            st.dataframe(niet_df[['activiteit', 'ruimte', 'startdatum', 'einddatum', 'groepgrootte']])
            csv = niet_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download lijst niet-herplaatsbare activiteiten", csv, "niet_herplaatsbaar.csv", "text/csv")

else:
    st.info("Upload beide bestanden om te starten met de simulatie.")
