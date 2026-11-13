"""Synthetic fixtures test the plot reducer, never serve as simulation evidence."""
import numpy as np


def test_video_reducer_preserves_narrow_peak_and_endpoints():
    from video.data_pipeline import extrema_reduce
    t=np.arange(1000,dtype=float);y=np.zeros(1000);y[511]=90.;y[514]=-40.
    tt,yy=extrema_reduce(t,y,100)
    assert tt[0]==0 and tt[-1]==999
    assert yy.max()==90 and yy.min()==-40
    assert np.all(np.diff(tt)>0)
    assert len(tt)<=202
