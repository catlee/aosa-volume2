all: nonaffine_transforms.pdf transform_tree.pdf pixel_snapping.pdf path_simplification.pdf

nonaffine_transforms.pdf: nonaffine_transforms.py
	python nonaffine_transforms.py

transform_tree.pdf: transform_tree.dot
	dot -Tpdf transform_tree.dot -o transform_tree.pdf

pixel_snapping.pdf: pixel_snapping.py
	python pixel_snapping.py

path_simplification.pdf: path_simplification.py
	python path_simplification.py
