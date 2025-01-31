# BSD 3-Clause License; see https://github.com/scikit-hep/awkward-1.0/blob/main/LICENSE

import awkward as ak

np = ak.nplikes.NumpyMetadata.instance()


@ak._connect.numpy.implements("ravel")
def ravel(array, highlevel=True, behavior=None):
    """
    Args:
        array: Data containing nested lists to flatten
        highlevel (bool): If True, return an #ak.Array; otherwise, return
            a low-level #ak.contents.Content subclass.
        behavior (None or dict): Custom #ak.behavior for the output array, if
            high-level.

    Returns an array with all level of nesting removed by erasing the
    boundaries between consecutive lists.

    This is the equivalent of NumPy's `np.ravel` for Awkward Arrays.

    Consider the following doubly nested `array`.

        ak.Array([[
                   [1.1, 2.2, 3.3],
                   [],
                   [4.4, 5.5],
                   [6.6]],
                  [],
                  [
                   [7.7],
                   [8.8, 9.9]
                  ]])

    Ravelling the array produces a flat array

        >>> print(ak.ravel(array))
        [1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7, 8.8, 9.9]

    Missing values are not eliminated by flattening. See #ak.flatten with `axis=None`
    for an equivalent function that eliminates the option type.
    """
    with ak._errors.OperationErrorContext(
        "ak.ravel",
        dict(array=array, highlevel=highlevel, behavior=behavior),
    ):
        return _impl(array, highlevel, behavior)


def _impl(array, highlevel, behavior):
    layout = ak.operations.to_layout(array, allow_record=False, allow_other=False)

    out = layout.completely_flatten(function_name="ak.ravel", drop_nones=False)
    assert isinstance(out, tuple) and all(
        isinstance(x, ak.contents.Content) for x in out
    )

    result = out[0].mergemany(out[1:])

    return ak._util.wrap(result, behavior, highlevel, like=array)
