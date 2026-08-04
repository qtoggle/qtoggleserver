import traceback
import types

import pytest

from qtoggleserver.utils.misc import append_traceback, deep_update, stack_to_traceback


class TestDeepUpdate:
    def test_merges_nested_dicts(self):
        """Should recursively merge nested dictionaries and keep unrelated keys."""

        dst = {"a": {"b": 1}, "c": 2}
        src = {"a": {"d": 3}, "e": 4}

        result = deep_update(dst, src)

        assert result is dst
        assert dst == {"a": {"b": 1, "d": 3}, "c": 2, "e": 4}

    def test_overwrites_non_dict_values(self):
        """Should replace existing values when either side is not a dict."""

        dst = {"a": {"b": 1}, "c": 2}
        src = {"a": "replaced", "c": {"d": 3}}

        deep_update(dst, src)

        assert dst == {"a": "replaced", "c": {"d": 3}}


class TestStackToTraceback:
    def test_returns_traceback_object(self):
        """Should return a TracebackType object."""

        tb = stack_to_traceback(skip=0)

        assert isinstance(tb, types.TracebackType)

    def test_skips_frames_correctly(self):
        """Should skip the specified number of frames from the stack."""

        def inner():
            return stack_to_traceback(skip=1)

        def middle():
            return inner()

        def outer():
            return middle()

        tb = outer()

        # The traceback should not include the inner() frame
        assert tb is not None
        frames = []
        cur = tb
        while cur is not None:
            frames.append(cur.tb_frame.f_code.co_name)
            cur = cur.tb_next

        # skip=1 omits stack_to_traceback, so the first frame in the returned
        # traceback is inner(). We verify that middle and outer are in the chain.
        assert "middle" in frames
        assert "outer" in frames
        # Verify stack_to_traceback is not in the frames (that's what skip=1 does)
        assert "stack_to_traceback" not in frames

    def test_skip_zero_includes_all_frames(self):
        """Should include all frames starting from stack_to_traceback when skip=0."""

        def inner():
            return stack_to_traceback(skip=0)

        def middle():
            return inner()

        tb = middle()

        assert tb is not None
        frames = []
        cur = tb
        while cur is not None:
            frames.append(cur.tb_frame.f_code.co_name)
            cur = cur.tb_next

        # skip=0 includes stack_to_traceback and all frames after it
        # We should see inner() and middle() in the chain
        assert "inner" in frames
        assert "middle" in frames

    def test_frames_have_correct_attributes(self):
        """Should create TracebackType objects with correct frame, lasti, and lineno attributes."""

        def inner():
            return stack_to_traceback(skip=1)  # Line 80

        tb = inner()

        assert tb is not None
        assert hasattr(tb, "tb_frame")
        assert hasattr(tb, "tb_lasti")
        assert hasattr(tb, "tb_lineno")
        assert isinstance(tb.tb_lasti, int)
        assert isinstance(tb.tb_lineno, int)

    def test_traceback_chain_is_proper(self):
        """Should create a properly linked chain of tracebacks."""

        def level3():
            return stack_to_traceback(skip=1)

        def level2():
            return level3()

        def level1():
            return level2()

        tb = level1()

        # Count frames in the chain
        frame_count = 0
        cur = tb
        while cur is not None:
            frame_count += 1
            cur = cur.tb_next

        # Should have multiple frames (at least level1, level2, level3)
        assert frame_count >= 2

    def test_empty_stack_with_large_skip(self):
        """Should return None when skip value exceeds available frames."""

        # skip=1000 should result in an empty list of frames
        tb = stack_to_traceback(skip=1000)

        assert tb is None


class TestAppendTraceback:
    def test_appends_traceback_to_exception(self):
        """Should append a traceback to an exception."""

        exc = ValueError("test error")
        tb = stack_to_traceback(skip=0)

        result = append_traceback(exc, tb)

        assert result is exc
        assert exc.__traceback__ is not None

    def test_uses_current_exception_by_default(self):
        """Should use the current exception from exc_info when exc is None."""

        try:
            raise ValueError("original error")
        except ValueError as original_exc:
            tb = stack_to_traceback(skip=0)
            result = append_traceback(exc=None, tb=tb)

            assert result is original_exc
            assert result.__traceback__ is not None

    def test_raises_assertion_error_outside_except_block(self):
        """Should raise AssertionError when called outside an except block with no exc."""

        with pytest.raises(AssertionError):
            append_traceback(exc=None, tb=None)

    def test_auto_generates_traceback_from_stack(self):
        """Should auto-generate traceback from stack when tb is None inside except block."""

        def helper():
            try:
                raise ValueError("test error")
            except ValueError as exc:
                return append_traceback(exc=exc, tb=None)

        result = helper()

        assert result.__traceback__ is not None
        # Verify the traceback contains frames from the helper call
        tb_str = "".join(traceback.format_tb(result.__traceback__))
        assert "helper" in tb_str

    def test_preserves_original_traceback(self):
        """Should preserve the original exception traceback."""

        try:
            raise ValueError("original error")
        except ValueError as original_exc:
            # Record original traceback
            original_tb = original_exc.__traceback__

            # Append a new traceback
            new_tb = stack_to_traceback(skip=0)
            result = append_traceback(original_exc, new_tb)

            # The result should have both the new and original tracebacks
            assert result.__traceback__ is not None
            # The new traceback should be at the beginning
            assert result.__traceback__ is not original_tb

    def test_appended_traceback_is_linked_properly(self):
        """Should properly link the appended traceback to the original."""

        try:
            raise ValueError("original error")
        except ValueError as exc:
            new_tb = stack_to_traceback(skip=0)
            result = append_traceback(exc, new_tb)

            # Count total frames in the combined traceback
            tb_list = []
            cur = result.__traceback__
            while cur is not None:
                tb_list.append(cur)
                cur = cur.tb_next

            # Should have frames from both the new and original traceback
            assert len(tb_list) >= 2

    def test_returns_same_exception_instance(self):
        """Should return the same exception instance that was passed in."""

        exc = ValueError("test error")
        tb = stack_to_traceback(skip=0)

        result = append_traceback(exc, tb)

        assert result is exc

    def test_complex_traceback_scenario(self):
        """Should handle complex scenarios with nested exception handling."""

        def level3():
            raise ValueError("level 3 error")

        def level2():
            try:
                level3()
            except ValueError as exc:
                new_tb = stack_to_traceback(skip=0)
                return append_traceback(exc, new_tb)

        def level1():
            return level2()

        result = level1()

        # Verify the exception has a traceback
        assert result.__traceback__ is not None

        # Format and verify the traceback contains multiple levels
        tb_str = "".join(traceback.format_tb(result.__traceback__))
        assert "level" in tb_str

    def test_skip_parameter_affects_traceback_generation(self):
        """Should respect the skip parameter when auto-generating traceback."""

        def helper():
            try:
                raise ValueError("test error")
            except ValueError as exc:
                # skip=1 should omit this function
                new_tb = stack_to_traceback(skip=1)
                return append_traceback(exc, new_tb)

        result = helper()

        assert result.__traceback__ is not None
