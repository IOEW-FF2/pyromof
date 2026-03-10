

# define the path to the used data in results folder

daten = Path("./results/stromflex_h2/results/sequences.csv")


# define a function to sort the 'b_biomass_dry to pyrolysis' column in descending order and return the sorted column as a pandas Series called sorted_column
def biomass_duration_curve(daten):
    print("Pfad:", daten)
    print("Existiert:", daten.exists())
    df = pd.read_csv(daten, index_col=0, parse_dates=True, sep=";")
    print("Spalten:", df.columns)
    sorted_column_biomass = df['b_biomass_dry to pyrolysis'].sort_values(ascending=False)
    return sorted_column_biomass

sorted_biomass_curve = biomass_duration_curve(daten)
print(sorted_biomass_curve.head())


# Plot the sorted_biomass_curve of the 'b_biomass_dry to pyrolysis' column

plt.figure(figsize=(10, 6))
plt.plot(range(len(sorted_biomass_curve)), sorted_biomass_curve.values)
plt.xlabel('Hours')
plt.ylabel('biomass load for pyrolysis')
plt.title('biomass duration curve')
plt.grid(True)


# save the plot in the results folder and show plot

plt.savefig('./results/stromflex_h2/results/biomass_duration_curve.png')
plt.show()
