import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from datetime import datetime

# Data from the image
data = {
    'Date': [
        '4/10/26', '4/9/26', '4/8/26', '4/7/26', '4/6/26', '4/5/26', '4/4/26', 
        '4/3/26', '4/2/26', '4/1/26', '3/31/26', '3/30/26', '3/29/26', '3/28/26', 
        '3/27/26', '3/26/26', '3/25/26'
    ],
    'Unique IPs': [
        996, 1034, 1112, 1156, 782, 979, 711, 1050, 745, 877, 1046, 896, 1029, 
        583, 634, 808, 784
    ]
}

df = pd.DataFrame(data)
df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y')
df = df.sort_values('Date').reset_index(drop=True)

# Save to CSV as per instructions
df.to_csv('unique_ips_data.csv', index=False)

# Convert dates to days from the start
start_date = df['Date'].min()
df['Days'] = (df['Date'] - start_date).dt.days

# Define the model: Linear + 7-day Periodic (Sine wave)
def model_func(t, m, b, A, phi):
    # Period is fixed at 7 days
    return m * t + b + A * np.sin(2 * np.pi * t / 7 + phi)

# Initial guesses
# m: slope (difference in IPs over 17 days / 17)
# b: intercept (around 700-800)
# A: amplitude (around 100-200)
# phi: phase (0)
p0 = [10, 700, 150, 0]

# Fit the model
params, params_covariance = curve_fit(model_func, df['Days'], df['Unique IPs'], p0=p0)

m_fit, b_fit, A_fit, phi_fit = params

# Generate fit line
t_fit = np.linspace(0, df['Days'].max(), 100)
y_fit = model_func(t_fit, *params)

# Plotting
plt.scatter(df['Date'], df['Unique IPs'], label='Original Data', color='blue')
plt.plot(pd.to_datetime(t_fit, unit='D', origin=start_date), y_fit, label='Linear + Weekly Fit', color='red')
plt.xlabel('Date')
plt.ylabel('Unique IPs')
plt.title('Unique IPs: Linear + 7-Day Periodic Fit')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('fit_plot.png')

print(f"Fit Parameters: m={m_fit:.2f}, b={b_fit:.2f}, A={A_fit:.2f}, phi={phi_fit:.2f}")
print(df)
