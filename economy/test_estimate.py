import unittest
import numpy as np
from estimate import decode, series

class JsonStatTests(unittest.TestCase):
    def test_sparse_dimensions_follow_declared_indices(self):
        d={'id':['geo','time'],'size':[2,3], 'dimension':{'geo':{'category':{'index':{'B':1,'A':0}}},'time':{'category':{'index':{'2022':2,'2020':0,'2021':1}}}}, 'value':{'0':10,'2':12,'4':21}}
        frame=decode(d)
        self.assertEqual(series(frame,geo='A').to_dict(),{'2020':10.,'2022':12.})
        self.assertEqual(series(frame,geo='B').to_dict(),{'2021':21.})
        with self.assertRaises(ValueError):
            series(decode({**d,'value':{'0':1,'3':2}}))
    def test_dense_nulls_are_missing_not_zero(self):
        d={'id':['time'],'size':[3],'dimension':{'time':{'category':{'index':{'a':0,'b':1,'c':2}}}},'value':[1,None,0]}
        self.assertEqual(series(decode(d)).to_dict(),{'a':1.,'c':0.})

if __name__=='__main__': unittest.main()
