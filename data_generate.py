#!/usr/bin/env python3
from datetime import datetime
import sys
import pandas as pd
import gurobipy as gp
from gurobipy import tupledict,tuplelist
from gurobipy import read
from gurobipy import GRB
import datetime
import random

sys.path.append('../')
__all__ = ["MRPModel"]

'''
2023-11-28
-基于公开MRP模型 


输入:
input_param: dict  模型参数

input_source_data: dict


输出:


'''
class MRPModel:
    name = "MRPModel"
    version = '0.1.0'

    def linear_max(self, m, max_var, var_fair, type_list, name):
        '''
        线性化max方法
        '''
        M = 1e5
        u_var = m.addVars(type_list,vtype=GRB.BINARY, name='u_max_'+name)
        m.addConstrs((max_var >= var_fair[i] for i in type_list))
        m.addConstrs((max_var <= var_fair[i]+M*(1-u_var[i]) for i in type_list))
        m.addConstr(gp.quicksum(u_var)>=1)
    
    def linear_min(self, m, min_var, var_fair, type_list, name):
        '''
        线性化min方法
        '''
        # M = 1e5
        # u_var = m.addVars(type_list,vtype=GRB.BINARY, name='u_min_'+name)
        m.addConstrs((min_var <= var_fair[i] for i in type_list))
        # m.addConstrs((min_var >= var_fair[i]-M*(1-u_var[i]) for i in type_list))
        # m.addConstr(gp.quicksum(u_var)>=1)        

    def mrp_opt_solver(self, dataset, input_param={}):
        ###data pre for model
        ##1.data frame

        ##2.constant dict
        # InvS[j] --物料j的初始库存
        # InvN[j,t]--物料j在时间t的到货量
	    # DmdQty[i,t]--成品i在时间的需求数量        
        # Jmust[i] --需求i的必选物料j列表
        # Jalt[i]--需求i的可选物料j列表字典
        # Alpha[K,k] -- 为了生产K对应k物料用量的倒数
        # p[j,t]--在时间t制造单个物料j的成本
        # s[j,t]--在时间t购买单个物料j的成本
        # h[j,t]--在时间t持有单个物料j的成本
        # c[i,j,t]--在时间t用物料j制造单个成品i的转换成本

        ##2.constant list
        algo_configs = input_param
        # self.logs = input_param['LOGS']
        InvS = dataset['InvS']
        InvN = dataset['InvN']
        DmdQty = dataset['DmdQty']
        Jmust = dataset['Jmust']
        Jalt = dataset['Jalt']
        Alpha = dataset['Alpha']
        p = dataset['p']
        s = dataset['s']
        h = dataset['h']
        c = dataset['c']

        # 基础部分下标
        J_T_dict = dataset['J_T_dict']
        I_J_T_dict = dataset['I_J_T_dict']


        # 下标字典转换
        J_T_tuplelist,  _ = gp.multidict(J_T_dict)
        I_J_T_tuplelist,  _ = gp.multidict(I_J_T_dict)

        print("读取数据完成，开始建模")
 

        stage_start = datetime.datetime.now()
        
        # 模型定义
        m = gp.Model("MRP_new")

        try:
            time_limit = input_param['SOLVER_TIME']
        except:
            time_limit = 3600

        ##变量定义
        X = m.addVars(J_T_tuplelist, lb = 0.0, name = 'X')        # [j,t]物料j在时间节点为t，通过制造得到的数量；
        Y = m.addVars(J_T_tuplelist, lb = 0.0, name = 'Y')      # [j,t]物料j在时间节点为t，通过购买得到的数量；
        H = m.addVars(J_T_tuplelist, lb = 0.0, name = 'H')        # [j,t]物料j在时间节点为t结尾，剩余库存的数量；

        W = m.addVars(I_J_T_tuplelist, lb = 0.0, name = 'W')  #[i,j,t]在时间节点为t，为了制造成品i所要花费的物料j的数量；


        #-----------------------------------开始构建约束---------------------------------------------
        # C1: 库存平衡约束
        m.addConstrs((InvS[ind[0]] + X[ind] + Y[ind] + InvN[ind] == gp.quicksum(W.select('*', ind[0],ind[1])) \
                      + H[ind] for ind in J_T_tuplelist if ind[1] == 1), name = 'inv_balance_initial' )        
        m.addConstrs((H[ind[0],ind[1]-1] + X[ind] + Y[ind] + InvN[ind]== gp.quicksum(W.select('*', ind[0],ind[1])) \
                      + H[ind] for ind in J_T_tuplelist if ind[1] > 1), name = 'inv_balance' ) 

        
        # C2 物料用量约束
        # 非替换组约束
        m.addConstrs((Alpha[ind[0],ind[1]]*W[ind] == DmdQty[ind[0],ind[2]] \
                      for ind in I_J_T_tuplelist if ind[1] in Jmust[ind[0]]), name = 'pn_for_must') 

        ##替换组约束
        for ind in DmdQty.keys():
            for j in Jmust[ind[0]]:
                m.addConstr(Alpha[ind[0],j]*W[ind[0],j,ind[1]] == DmdQty[ind], name = 'pn_for_must')
            for alt, alt_list in Jalt[ind[0]].items():
                m.addConstr(gp.quicksum(Alpha[ind[0],j]*W[ind[0],j,ind[1]] for j in alt_list) == DmdQty[ind], \
                            name = 'pn_for_alt')


        # 目标函数定义


        obj_10 = m.addVar(name='obj_10')

        m.addConstr(obj_10 == gp.quicksum(X[ind]*p[ind]+Y[ind]*s[ind]+H[ind]*h[ind] for ind in J_T_tuplelist))

        obj_12 = gp.quicksum(W[ind]*c[ind] for ind in I_J_T_tuplelist)
        #m.addConstr(obj_12 == gp.quicksum(1-gp.quicksum(X.select(i,'*'))/DmdQty[i] for i in demand_id_list))        
        # obj_1 = m.addVar(name = 'obj_1')
        # m.addConstr(obj_1 ==  obj_12  )


        obj = obj_10 + obj_12 
        m.setObjective(obj)
        print("建模完成")
        T = algo_configs['T']
        I_size = algo_configs['I_size']
        J_size = algo_configs['J_size']
        outdir  = algo_configs['file_dir']
        # m.write("MRP_model_T"+str(T)+'_I'+str(I_size)+'_J'+str(J_size)+".mps")

        stage_pro = datetime.datetime.now()
        stage_time = (stage_pro-stage_start).seconds
        timestr = stage_pro.strftime("%Y%m%d%H%M%S")
        filename = "MRP_model_T"+str(T)+'_I'+str(I_size)+'_J'+str(J_size)+'_'+timestr+".mps"



        m.write(outdir + filename)
        print("建模时间：{}".format(stage_time))
        print("mps file save in:")
        print(outdir + filename) 

        # m.Params.timeLimit = time_limit
        
        
        # print("******* 模型开始求解 *******")
        # m.optimize()
        # print("******* 模型求解完成 *******")
        # stage_end = datetime.datetime.now()
        # stage_time = (stage_end-stage_pro).seconds
        # print("求解时间：{}".format(stage_time))        

        # if m.status == GRB.Status.INFEASIBLE:
        #     print('main model不可解')
        #     res_dict['model_flag'] = 5
        #     return(res_dict)


        # X_r = pd.DataFrame([[k[0], k[1], v.X] for k, v in tqdm(X.items(), desc='X output')], 
        #                     columns = ['MATID', 'DATEID', 'QTY'])
        # Y_r = pd.DataFrame([[k[0], k[1], v.X] for k, v in tqdm(Y.items(), desc='Y output')],
        #                     columns = ['MATID', 'DATEID', 'QTY'])
        # H_r = pd.DataFrame([[k[0], k[1], v.X] for k, v in tqdm(H.items(), desc='H output')],
        #                     columns = ['MATID', 'DATEID', 'QTY'])
        # W_r = pd.DataFrame([[k[0], k[1], k[2], v.X] for k, v in tqdm(W.items(), desc='W output')], 
        #                     columns = ['EMID', 'MATID', 'DATEID', 'QTY'])

        # res_dict = {}
        # res_dict['X'] = X_r
        # res_dict['Y'] = Y_r
        # res_dict['H'] = H_r
        # res_dict['W'] = W_r


        # stage_end = datetime.datetime.now()
        # stage_time = (stage_end-stage_pro).seconds
        # print('model solve time: {}'.format(stage_time))
        # print("******* 算法求解完成 *******")
        return {}

    def data_gener(self,input_param={}):
    ###data gener for model
        print("开始生成数据")
        data_dict = {}
        try:
            maxT = input_param['T']
        except:
            maxT = 200
        try:
            I_size = input_param['I_size']
        except:
            I_size = 1500  
        try:
            J_size = input_param['J_size']
        except:
            J_size = 3000                       
        
        datelist = list(range(1,maxT+1))
        I = list(range(I_size))
        J = list(range(J_size))
        df_t = pd.DataFrame({"DATEID":datelist})
        df_t['value'] = 1
        df_I = pd.DataFrame({"EMID":I})
        df_I['value'] = 1 
        df_J = pd.DataFrame({"MATID":J})
        df_J['value'] = 1

        df_J_T = pd.merge(df_t, df_J, on='value')
        df_I_T = pd.merge(df_t, df_I, on='value')

        Jmust = {}
        Jalt = {}
        df_I_J = pd.DataFrame()
        for i in I:
            if maxT >= 150 and I_size >= 1000 and J_size >= 3000:
                j_num = random.randint(round(J_size/200,0), round(J_size/50,0))
            else:
                j_num = random.randint(round(J_size/100,0), round(J_size/20,0))
            jmust_num = random.randint(1,int(j_num/2))
            jalt_max = int(round((j_num - jmust_num)/3,0))
            all_j = random.sample(J,j_num)
            Jmust[i] = all_j[:jmust_num]
            Jalt[i] = {}
            jalt_num = 0
            for alt in range(jalt_max):
                alt_size = random.randint(2,10)
                if alt_size+jalt_num+jmust_num <= j_num:
                    Jalt[i][alt] = all_j[(jalt_num+jmust_num):(alt_size+jalt_num+jmust_num)]
                else:
                    break
                jalt_num += alt_size
            
            df_temp = pd.DataFrame({"MATID":all_j[:(jalt_num+jmust_num)]})
            df_temp['EMID'] = i

            df_I_J = pd.concat([df_I_J, df_temp])
        
        df_I_J['value'] = 1
        df_I_J_T = pd.merge(df_t, df_I_J, on='value')

        df_J['invs'] = [random.randint(0,100) for j in J]
        InvS = df_J.set_index(["MATID"])['invs'].to_dict()

        df_J_T['invn'] = [random.randint(0,50) for ind in range(len(df_J_T))]
        df_J_T['p'] = [random.uniform(10,50) for ind in range(len(df_J_T))]
        df_J_T['s'] = [random.uniform(15,45) for ind in range(len(df_J_T))]
        df_J_T['h'] = [random.uniform(0,20) for ind in range(len(df_J_T))]

        InvN = df_J_T.set_index(["MATID",'DATEID'])['invn'].to_dict()
        p = df_J_T.set_index(["MATID",'DATEID'])['p'].to_dict()
        h = df_J_T.set_index(["MATID",'DATEID'])['h'].to_dict()
        s = df_J_T.set_index(["MATID",'DATEID'])['s'].to_dict()
        J_T_dict = df_J_T.set_index(["MATID",'DATEID'])['value'].to_dict()

        df_I_T['dmd'] = [random.randint(100,10000) for ind in range(len(df_I_T))]
        DmdQty = df_I_T.set_index(["EMID",'DATEID'])['dmd'].to_dict()

        df_I_J['usage'] = [random.randint(1,10) for ind in range(len(df_I_J))]
        df_I_J['alpha'] = 1/df_I_J['usage']
        Alpha = df_I_J.set_index(["EMID",'MATID'])['alpha'].to_dict()    

        df_I_J_T['c'] = [random.uniform(0,10) for ind in range(len(df_I_J_T))]
        c = df_I_J_T.set_index(["EMID",'MATID','DATEID'])['c'].to_dict() 
        I_J_T_dict = df_I_J_T.set_index(["EMID",'MATID','DATEID'])['value'].to_dict()       

        data_dict['InvS'] = InvS
        data_dict['InvN'] = InvN
        data_dict['p'] = p
        data_dict['s'] = s
        data_dict['h'] = h
        data_dict['c'] = c
        data_dict['DmdQty'] = DmdQty
        data_dict['Jmust'] = Jmust
        data_dict['Jalt'] = Jalt
        data_dict['Alpha'] = Alpha
        data_dict['I_J_T_dict'] = I_J_T_dict 
        data_dict['J_T_dict'] = J_T_dict
        print("数据生成完成！")

        return(data_dict)
           


if __name__ == "__main__":
    # tt = mps_test(input_param)
    # print(res)
    print('For test.')
    argc = len(sys.argv)
    if argc < 2:
        print(sys.argv[0] +' requires 1 command line parameter:')
        print(sys.argv[0] + ' T_Isize_Jsize')
        print('')
        print('E.g.')
        print(sys.argv[0] + ' 150_2000_4000')
        sys.exit(1)
    elif argc >= 2:
        parstr = sys.argv[1]
        pars = parstr.split('_')
        input_param = {}
        if len(pars) == 3:
            input_param['T'] = int(pars[0])
            input_param['I_size'] = int(pars[1])
            input_param['J_size'] = int(pars[2])
        else:
            print('pls give correct parameters!')
            sys.exit(1)
        if argc == 3:
            file_dir = sys.argv[1]
        else:
            file_dir = "/home/solver/SOLVER_TEST/"
        input_param['file_dir'] = file_dir
                    
    ##类名
    # random.seed(2023)
    mrp_test = MRPModel()
    dataset = mrp_test.data_gener(input_param)
    res = mrp_test.mrp_opt_solver(dataset, input_param)