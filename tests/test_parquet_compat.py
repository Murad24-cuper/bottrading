import pandas as pd

from src.parquet_compat import assert_fastparquet_available, read_parquet, write_parquet


def test_fastparquet_roundtrip_works_when_pyarrow_is_loaded(tmp_path):
    import pyarrow
    path=tmp_path/'sample.parquet'
    frame=pd.DataFrame({'value':[1,2]})
    write_parquet(frame,path,index=False)
    loaded=read_parquet(path)
    pd.testing.assert_frame_equal(loaded,frame)
    assert pyarrow.__version__
    assert_fastparquet_available()
