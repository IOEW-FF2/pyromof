

# define the path to the used data in results folder

daten = ("./results/stromflex_h2/results/sequences.csv")


# define a function to sort the 'b_electricity to electricity_grid' column in descending order and return the sorted column as a pandas Series called sorted_column
def load_duration_curve(daten):
    print("Pfad:", daten)
    print("Existiert:", daten.exists())
    df = pd.read_csv(daten, index_col=0, parse_dates=True, sep=";")
    print("Spalten:", df.columns)
    sorted_column = df['b_electricity to electricity_grid'].sort_values(ascending=False)
    return sorted_column

sorted_load_curve = load_duration_curve(daten)
print(sorted_load_curve.head())


# Plot the sorted_load_curve of the 'b_electricity to electricity_grid' column

plt.figure(figsize=(10, 6))
plt.plot(range(len(sorted_load_curve)), sorted_load_curve.values)
plt.xlabel('Hours')
plt.ylabel('Injected Energy')
plt.title('Load duration curve')
plt.grid(True)


# save the plot in the results folder and show plot

plt.savefig('./results/stromflex_h2/results/load_duration_curve.png')
plt.show()
