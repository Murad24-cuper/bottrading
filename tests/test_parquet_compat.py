import pandas as pd

from src.parquet_compat import assert_no_pyarrow_loaded, read_parquet, write_parquet


def test_fastparquet_roundtrip_does_not_load_pyarrow(tmp_path):
    path=tmp_path/'sample.parquet'
    frame=pd.DataFrame({'value':[1,2]})
    write_parquet(frame,path,index=False)
    loaded=read_parquet(path)
    pd.testing.assert_frame_equal(loaded,frame)
    assert_no_pyarrow_loaded()
