import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

x = np.linspace(0, np.pi*2, 1000)
y = np.sin(x)
plt.plot(x, y)
plt.title('A simple plot')
plt.xlabel('time (s)')
plt.ylabel('voltage (mV)')
prop = font_manager.FontProperties(size=48)
plt.figtext(0.91, 0.9, r'$\mathcircled{1}$', fontproperties=prop)
plt.figtext(0.81, 0.8, r'$\mathcircled{2}$', fontproperties=prop)
plt.figtext(0.81, 0.52, r'$\mathcircled{3}$', fontproperties=prop)
plt.figtext(0.62, 0.91, r'$\mathcircled{4}$', fontproperties=prop)
plt.figtext(0.01, 0.3, r'$\mathcircled{5}$', fontproperties=prop)
plt.figtext(0.58, 0.01, r'$\mathcircled{6}$', fontproperties=prop)
plt.savefig('artists_figure.pdf')
