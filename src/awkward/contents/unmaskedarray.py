# BSD 3-Clause License; see https://github.com/scikit-hep/awkward-1.0/blob/main/LICENSE

import copy

import awkward as ak
from awkward.contents.content import Content, unset
from awkward.forms.unmaskedform import UnmaskedForm

np = ak.nplikes.NumpyMetadata.instance()
numpy = ak.nplikes.Numpy.instance()


class UnmaskedArray(Content):
    is_option = True

    def copy(
        self,
        content=unset,
        parameters=unset,
        nplike=unset,
    ):
        return UnmaskedArray(
            self._content if content is unset else content,
            self._parameters if parameters is unset else parameters,
            self._nplike if nplike is unset else nplike,
        )

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        return self.copy(
            content=copy.deepcopy(self._content, memo),
            parameters=copy.deepcopy(self._parameters, memo),
        )

    def __init__(self, content, parameters=None, nplike=None):
        if not isinstance(content, Content):
            raise ak._errors.wrap_error(
                TypeError(
                    "{} 'content' must be a Content subtype, not {}".format(
                        type(self).__name__, repr(content)
                    )
                )
            )
        if nplike is None:
            nplike = content.nplike

        self._content = content
        self._init(parameters, nplike)

    @property
    def content(self):
        return self._content

    Form = UnmaskedForm

    def _form_with_key(self, getkey):
        form_key = getkey(self)
        return self.Form(
            self._content._form_with_key(getkey),
            parameters=self._parameters,
            form_key=form_key,
        )

    def _to_buffers(self, form, getkey, container, nplike):
        assert isinstance(form, self.Form)
        self._content._to_buffers(form.content, getkey, container, nplike)

    @property
    def typetracer(self):
        tt = ak._typetracer.TypeTracer.instance()
        return UnmaskedArray(
            self._content.typetracer,
            self._parameters,
            tt,
        )

    @property
    def length(self):
        return self._content.length

    def _forget_length(self):
        return UnmaskedArray(
            self._content._forget_length(),
            self._parameters,
            self._nplike,
        )

    def __repr__(self):
        return self._repr("", "", "")

    def _repr(self, indent, pre, post):
        out = [indent, pre, "<UnmaskedArray len="]
        out.append(repr(str(self.length)))
        out.append(">")
        out.extend(self._repr_extra(indent + "    "))
        out.append("\n")
        out.append(self._content._repr(indent + "    ", "<content>", "</content>\n"))
        out.append(indent + "</UnmaskedArray>")
        out.append(post)
        return "".join(out)

    def merge_parameters(self, parameters):
        return UnmaskedArray(
            self._content,
            ak._util.merge_parameters(self._parameters, parameters),
            self._nplike,
        )

    def toIndexedOptionArray64(self):
        arange = self._nplike.index_nplike.arange(self._content.length, dtype=np.int64)
        return ak.contents.IndexedOptionArray(
            ak.index.Index64(arange, nplike=self.nplike),
            self._content,
            self._parameters,
            self._nplike,
        )

    def toByteMaskedArray(self, valid_when):
        return ak.contents.ByteMaskedArray(
            ak.index.Index8(
                self.mask_as_bool(valid_when).view(np.int8), nplike=self.nplike
            ),
            self._content,
            valid_when,
            self._parameters,
            self._nplike,
        )

    def toBitMaskedArray(self, valid_when, lsb_order):
        bitlength = int(numpy.ceil(self._content.length / 8.0))
        if valid_when:
            bitmask = self._nplike.full(bitlength, np.uint8(255), dtype=np.uint8)
        else:
            bitmask = self._nplike.zeros(bitlength, dtype=np.uint8)

        return ak.contents.BitMaskedArray(
            ak.index.IndexU8(bitmask),
            self._content,
            valid_when,
            self.length,
            lsb_order,
            self._parameters,
            self._nplike,
        )

    def mask_as_bool(self, valid_when=True, nplike=None):
        if nplike is None:
            nplike = self._nplike

        if valid_when:
            return nplike.index_nplike.ones(self._content.length, dtype=np.bool_)
        else:
            return nplike.index_nplike.zeros(self._content.length, dtype=np.bool_)

    def _getitem_nothing(self):
        return self._content._getitem_range(slice(0, 0))

    def _getitem_at(self, where):
        if not self._nplike.known_data:
            return ak._typetracer.MaybeNone(self._content._getitem_at(where))

        return self._content._getitem_at(where)

    def _getitem_range(self, where):
        if not self._nplike.known_shape:
            return self

        start, stop, step = where.indices(self.length)
        assert step == 1
        return UnmaskedArray(
            self._content._getitem_range(slice(start, stop)),
            self._parameters,
            self._nplike,
        )

    def _getitem_field(self, where, only_fields=()):
        return UnmaskedArray(
            self._content._getitem_field(where, only_fields),
            None,
            self._nplike,
        )

    def _getitem_fields(self, where, only_fields=()):
        return UnmaskedArray(
            self._content._getitem_fields(where, only_fields),
            None,
            self._nplike,
        )

    def _carry(self, carry, allow_lazy):
        return UnmaskedArray(
            self._content._carry(carry, allow_lazy),
            self._parameters,
            self._nplike,
        )

    def _getitem_next_jagged(self, slicestarts, slicestops, slicecontent, tail):
        return UnmaskedArray(
            self._content._getitem_next_jagged(
                slicestarts, slicestops, slicecontent, tail
            ),
            self._parameters,
            self._nplike,
        )

    def _getitem_next(self, head, tail, advanced):
        if head == ():
            return self

        elif isinstance(
            head, (int, slice, ak.index.Index64, ak.contents.ListOffsetArray)
        ):
            return UnmaskedArray(
                self._content._getitem_next(head, tail, advanced),
                self._parameters,
                self._nplike,
            ).simplify_optiontype()

        elif isinstance(head, str):
            return self._getitem_next_field(head, tail, advanced)

        elif isinstance(head, list):
            return self._getitem_next_fields(head, tail, advanced)

        elif head is np.newaxis:
            return self._getitem_next_newaxis(tail, advanced)

        elif head is Ellipsis:
            return self._getitem_next_ellipsis(tail, advanced)

        elif isinstance(head, ak.contents.IndexedOptionArray):
            return self._getitem_next_missing(head, tail, advanced)

        else:
            raise ak._errors.wrap_error(AssertionError(repr(head)))

    def project(self, mask=None):
        if mask is not None:
            return ak.contents.ByteMaskedArray(
                mask,
                self._content,
                False,
                self._parameters,
                self._nplike,
            ).project()
        else:
            return self._content

    def simplify_optiontype(self):
        if isinstance(
            self._content,
            (
                ak.contents.IndexedArray,
                ak.contents.IndexedOptionArray,
                ak.contents.ByteMaskedArray,
                ak.contents.BitMaskedArray,
                ak.contents.UnmaskedArray,
            ),
        ):
            return self._content
        else:
            return self

    def num(self, axis, depth=0):
        posaxis = self.axis_wrap_if_negative(axis)
        if posaxis == depth:
            out = self.length
            if ak._util.is_integer(out):
                return np.int64(out)
            else:
                return out
        else:
            return ak.contents.UnmaskedArray(
                self._content.num(posaxis, depth), self._parameters, self._nplike
            )

    def _offsets_and_flattened(self, axis, depth):
        posaxis = self.axis_wrap_if_negative(axis)
        if posaxis == depth:
            raise ak._errors.wrap_error(np.AxisError("axis=0 not allowed for flatten"))
        else:
            offsets, flattened = self._content._offsets_and_flattened(posaxis, depth)
            if offsets.length == 0:
                return (
                    offsets,
                    UnmaskedArray(flattened, self._parameters, self._nplike),
                )

            else:
                return (offsets, flattened)

    def _mergeable(self, other, mergebool):
        if isinstance(
            other,
            (
                ak.contents.IndexedArray,
                ak.contents.IndexedOptionArray,
                ak.contents.ByteMaskedArray,
                ak.contents.BitMaskedArray,
                ak.contents.UnmaskedArray,
            ),
        ):
            return self._content.mergeable(other.content, mergebool)

        else:
            return self._content.mergeable(other, mergebool)

    def _reverse_merge(self, other):
        return self.toIndexedOptionArray64()._reverse_merge(other)

    def mergemany(self, others):
        if len(others) == 0:
            return self

        if all(isinstance(x, UnmaskedArray) for x in others):
            parameters = self._parameters
            tail_contents = []
            for x in others:
                parameters = ak._util.merge_parameters(parameters, x._parameters, True)
                tail_contents.append(x._content)

            return UnmaskedArray(
                self._content.mergemany(tail_contents),
                parameters,
                self._nplike,
            )

        else:
            return self.toIndexedOptionArray64().mergemany(others)

    def fill_none(self, value):
        return self._content.fill_none(value)

    def _local_index(self, axis, depth):
        posaxis = self.axis_wrap_if_negative(axis)
        if posaxis == depth:
            return self._local_index_axis0()
        else:
            return UnmaskedArray(
                self._content._local_index(posaxis, depth),
                self._parameters,
                self._nplike,
            )

    def numbers_to_type(self, name):
        return ak.contents.UnmaskedArray(
            self._content.numbers_to_type(name),
            self._parameters,
            self._nplike,
        )

    def _is_unique(self, negaxis, starts, parents, outlength):
        if self._content.length == 0:
            return True
        return self._content._is_unique(negaxis, starts, parents, outlength)

    def _unique(self, negaxis, starts, parents, outlength):
        if self._content.length == 0:
            return self
        return self._content._unique(negaxis, starts, parents, outlength)

    def _argsort_next(
        self,
        negaxis,
        starts,
        shifts,
        parents,
        outlength,
        ascending,
        stable,
        kind,
        order,
    ):
        out = self._content._argsort_next(
            negaxis,
            starts,
            shifts,
            parents,
            outlength,
            ascending,
            stable,
            kind,
            order,
        )

        if isinstance(out, ak.contents.RegularArray):
            tmp = ak.contents.UnmaskedArray(
                out._content,
                None,
                self._nplike,
            ).simplify_optiontype()

            return ak.contents.RegularArray(
                tmp,
                out._size,
                out._length,
                None,
                self._nplike,
            )

        else:
            return out

    def _sort_next(
        self, negaxis, starts, parents, outlength, ascending, stable, kind, order
    ):
        out = self._content._sort_next(
            negaxis,
            starts,
            parents,
            outlength,
            ascending,
            stable,
            kind,
            order,
        )

        if isinstance(out, ak.contents.RegularArray):
            tmp = ak.contents.UnmaskedArray(
                out._content,
                self._parameters,
                self._nplike,
            ).simplify_optiontype()

            return ak.contents.RegularArray(
                tmp,
                out._size,
                out._length,
                self._parameters,
                self._nplike,
            )

        else:
            return out

    def _combinations(self, n, replacement, recordlookup, parameters, axis, depth):
        posaxis = self.axis_wrap_if_negative(axis)
        if posaxis == depth:
            return self._combinations_axis0(n, replacement, recordlookup, parameters)
        else:
            return ak.contents.UnmaskedArray(
                self._content._combinations(
                    n, replacement, recordlookup, parameters, posaxis, depth
                ),
                self._parameters,
                self._nplike,
            )

    def _reduce_next(
        self,
        reducer,
        negaxis,
        starts,
        shifts,
        parents,
        outlength,
        mask,
        keepdims,
        behavior,
    ):
        return self._content._reduce_next(
            reducer,
            negaxis,
            starts,
            shifts,
            parents,
            outlength,
            mask,
            keepdims,
            behavior,
        )

    def _validity_error(self, path):
        if isinstance(
            self._content,
            (
                ak.contents.BitMaskedArray,
                ak.contents.ByteMaskedArray,
                ak.contents.IndexedArray,
                ak.contents.IndexedOptionArray,
                ak.contents.UnmaskedArray,
            ),
        ):
            return "{0} contains \"{1}\", the operation that made it might have forgotten to call 'simplify_optiontype()'"
        else:
            return self._content.validity_error(path + ".content")

    def _nbytes_part(self):
        return self.content._nbytes_part()

    def _pad_none(self, target, axis, depth, clip):
        posaxis = self.axis_wrap_if_negative(axis)
        if posaxis == depth:
            return self.pad_none_axis0(target, clip)
        elif posaxis == depth + 1:
            return self._content._pad_none(target, posaxis, depth, clip)
        else:
            return ak.contents.UnmaskedArray(
                self._content._pad_none(target, posaxis, depth, clip),
                self._parameters,
                self._nplike,
            )

    def _to_arrow(self, pyarrow, mask_node, validbytes, length, options):
        return self._content._to_arrow(pyarrow, self, None, length, options)

    def _to_numpy(self, allow_missing):
        content = ak.operations.to_numpy(self.content, allow_missing=allow_missing)
        if allow_missing:
            return self._nplike.ma.MaskedArray(content)
        else:
            return content

    def _completely_flatten(self, nplike, options):
        branch, depth = self.branch_depth
        if branch or options["drop_nones"] or depth > 1:
            return self.project()._completely_flatten(nplike, options)
        else:
            return [self.simplify_optiontype()]

    def _recursively_apply(
        self, action, behavior, depth, depth_context, lateral_context, options
    ):
        if options["return_array"]:

            def continuation():
                return UnmaskedArray(
                    self._content._recursively_apply(
                        action,
                        behavior,
                        depth,
                        copy.copy(depth_context),
                        lateral_context,
                        options,
                    ),
                    self._parameters if options["keep_parameters"] else None,
                    self._nplike,
                )

        else:

            def continuation():
                self._content._recursively_apply(
                    action,
                    behavior,
                    depth,
                    copy.copy(depth_context),
                    lateral_context,
                    options,
                )

        result = action(
            self,
            depth=depth,
            depth_context=depth_context,
            lateral_context=lateral_context,
            continuation=continuation,
            behavior=behavior,
            nplike=self._nplike,
            options=options,
        )

        if isinstance(result, Content):
            return result
        elif result is None:
            return continuation()
        else:
            raise ak._errors.wrap_error(AssertionError(result))

    def packed(self):
        return UnmaskedArray(self._content.packed(), self._parameters, self._nplike)

    def _to_list(self, behavior, json_conversions):
        out = self._to_list_custom(behavior, json_conversions)
        if out is not None:
            return out

        return self._content._to_list(behavior, json_conversions)

    def _to_nplike(self, nplike):
        content = self._content._to_nplike(nplike)
        return UnmaskedArray(
            content,
            parameters=self.parameters,
            nplike=nplike,
        )

    def _layout_equal(self, other, index_dtype=True, numpyarray=True):
        return self.content.layout_equal(other.content, index_dtype, numpyarray)
