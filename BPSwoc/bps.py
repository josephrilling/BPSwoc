# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_BPS.ipynb.

# %% auto 0
__all__ = ['BPS']

# %% ../nbs/00_BPS.ipynb 2
import nbdev
from nbdev.showdoc import *

from scipy.linalg import cholesky
import scipy.special as ss
import pandas as pd
import numpy as np

# %% ../nbs/00_BPS.ipynb 4
class BPS:
    "Bayesian Predictive Synthesis: A latent ensemble forecasting method new version101"
    def __init__(self, 
                 y:float, 
                 a_j, 
                 A_j, 
                 n_j, 
                 delta, 
                 m_0,
                 C_0, 
                 n_0, 
                 s_0, 
                 burn_in:int, 
                 mcmc_iter:int): 
        self.y = y
        self.a_j = a_j
        self.A_j = A_j
        self.n_j = n_j
        self.delta = delta
        self.m_0 = m_0
        self.C_0 = C_0
        self.n_0 = n_0
        self.s_0 = s_0
        self.burn_in = burn_in
        self.mcmc_iter = mcmc_iter
        self.module_name = "BPS"
    def fit(self):
        "A way to fit the model"
        def std_var(x):
            return (x + np.transpose(x))/2

        def chol(A):
            '''returns upper triangle of matrix'''
            return cholesky(A, lower = False)       
        
        y =self.y[0:-1]
        a_j =self.a_j[0:-1,]
        A_j =self.A_j[0:-1,]
        n_j =self.n_j 
        delta =self.delta 
        m_0 = self.m_0
        C_0 =self.C_0
        n_0 =self.n_0 
        s_0 =self.s_0 
        burn_in = self.burn_in
        mcmc_iter = self.mcmc_iter
        mcmc_iter = self.burn_in + self.mcmc_iter
        T = y.shape[0]
        p_x = a_j.shape[1]
        p = p_x + 1
        self.p = p
        self.p_x= p_x
        m_t = np.zeros(shape = [T + 1, p])
        C_t = np.zeros(shape = [(T + 1) * p, p])
        n_t = np.zeros(shape = [T + 1, 1])
        s_t = np.zeros(shape = [T + 1, mcmc_iter])
        v_t = np.zeros(shape = [T, mcmc_iter])
        a_t = np.zeros(shape = [T, p])
        R_t = np.zeros(shape = [T * p, p])
        f_t = np.zeros(shape = [T, 1])
        q_t = np.zeros(shape = [T, 1])
        phi_t = np.zeros(shape = [T, p_x])
        X_t = np.zeros(shape = [T, p_x * (mcmc_iter + 1)])
        theta_t = np.zeros(shape = [T, p * mcmc_iter])
        a_k = np.zeros(shape = [mcmc_iter, p])
        R_k = np.zeros(shape = [p * mcmc_iter,  p])
        v_k = np.zeros(shape = [mcmc_iter, 1])
        n_k = np.zeros(shape = [1,1])

        d = delta[0]
        beta = delta[1]

        m_t[0, :] = m_0 # replace the initial mean at time t with prior mean
        C_t[0:p, :] = C_0 # replace the initial variance at time t with prior variance
        n_t[0] = n_0 # replace the initial dof at time t with prior dof
        s_t[0, :] = s_0 # replace the initial obs var at time t with prior obs var


        for t in range(T):
            phi_t[t, :] = (0.5 * beta * n_j[t, :])/np.random.gamma(beta * n_j[t, :]/2)
            X_t[t, 0:p_x] = a_j[t, :] + \
                np.matmul(np.random.normal(size = [1, a_j[t, :].shape[0]]), chol(std_var(np.diag(phi_t[t, :] * A_j[t, :]))))
                        
        for i in range(mcmc_iter):
            if i % 1000== 0:
              print(i)
        # forward filter
            for t in range(T):
                F_t = np.hstack([1, X_t[t, (p_x * (i + 1)- (p_x - 1) - 1):(p_x * (i + 1))]]) # may run into problems bc this is a column in matlab
                a_t[t, :] = m_t[t, :] # prior for time t
                R_t[(p*(t + 1) - (p - 1) - 1) : (p*(t + 1)),:] = C_t[(p*(t + 1) - p) : (p*(t + 1)),:]/d # might need to check indexing 
            # prediction at time t
                f_t[t] = np.matmul(F_t, a_t[t, :].T)
                q_t[t] = np.matmul(F_t, np.matmul(C_t[(p*(t + 1) - (p - 1) - 1) : (p*(t + 1)),:], F_t/d)) + s_t[t, i]
            # compute forecast error and adaptive vector
                e_t = y[t] - f_t[t]
                A_t = np.matmul(R_t[(p*(t + 1) - (p - 1) - 1) : (p*(t + 1)), : ], F_t/q_t[t])
            # posterior for time t
                n_t[t + 1] = beta * n_t[t] + 1 # might need to check indexing here
                r_t = (beta * n_t[t] + e_t**2/q_t[t])/n_t[t + 1]
                s_t[t + 1, i] = r_t * s_t[t, i]
                m_t[t + 1, :] = a_t[t, :] + np.matmul(A_t.reshape([A_t.shape[0], 1]), e_t).T
                C_t[p * (t + 2) - p:(p * ( t + 2)), :] = std_var(r_t * \
                                                                 (R_t[(p*(t + 1) - p) : (p*(t + 1)),:] - q_t[t] * \
                                                                  np.matmul(A_t.reshape([A_t.shape[0], 1]), A_t.reshape(1, A_t.shape[0]))))
        # sample theta at T
            v_t[-1, i] = 1/np.random.gamma(shape = n_t[-1]/2, scale = 2/(n_t[-1] * s_t[-1, i]))
            theta_t[T - 1, (p * (i + 1) - p):(p * (i + 1))] = m_t[-1, :] + np.matmul(np.random.normal(size = [1, len(m_t[-1, :])]),
                                                                                 chol(std_var(C_t[-p:, :] * (v_t[-1, i]/s_t[-1, i]))))
            n_k = beta * n_t[-1] + 1
        # break
            v_k[i] = 1/np.random.gamma(beta * n_t[-1]/2, 2/(beta * n_t[-1]*s_t[-1, i]))
            a_k[i, :] = m_t[-1, :]
            R_k[p*i:(p * (i + 1)), :] = C_t[-p:, :]/d * v_k[i, 0]/s_t[-1, i]
            
        # backward-sampler
            for t in range(T - 2, -1, -1):
                v_t[t, i] = 1/(1/v_t[t + 1, i] * beta + \
                               np.random.gamma(shape = (1 - beta)*n_t[t + 1]/2,scale = 2/(n_t[t + 1] * s_t[t + 1, i])))
                m_star_t = m_t[t + 1, :] + d * (theta_t[t + 1, (p * i):(p * (i + 1))] -a_t[t+1, :]) ## This line is updated
                C_star_t = C_t[(p * (t+1)):(p * (t + 2)), :] * (1 - d) * (v_t[t, i]/s_t[t + 1, i])
                theta_t[t, (p * i):(p * ( i + 1))] = m_star_t + \
                    np.matmul(np.random.normal(size = [1, len(m_star_t)]), chol(std_var(C_star_t)))

        # sample X_t
            for t in range(0, T):
                A_st = np.diag(phi_t[t,:] * A_j[t, :])
                a_st = a_j[t, :]
                theta_p = theta_t[t, (p*(i + 1) - p + 1):(p*(i + 1))]
                theta_1 = theta_t[t, p*(i + 1) - p]
                sigma = np.matmul(theta_p, A_st)/(v_t[t, i] + np.matmul(np.matmul(theta_p, A_st), theta_p))
                a_star = a_st + sigma*(y[t] - (theta_1 + np.matmul(theta_p, a_st)))
                A_star = std_var(A_st - np.matmul(np.matmul(A_st, theta_p.reshape([theta_p.shape[0], 1])), sigma.reshape([1, sigma.shape[0]])))
                X_t[t, (p_x*(i + 1)):(p_x*(i + 2))] = a_star + np.matmul(np.random.normal(size = [1, len(a_star)]), chol(std_var(A_star)))
                phi_t[t, :] = (0.5 * (n_j[t, :] + 1))/np.random.gamma((n_j[t, :] + (X_t[t, (p_x*(i + 1)):(p_x * (i + 2))] - a_st)**2/A_j[t, :])/2)

        self.theta_post_samples = theta_t[:, (burn_in*p_x):]
        self.X_post_samples = X_t[:, (burn_in * p_x):]
        self.a_k_samples = a_k[burn_in:, :]
        self.R_k_samples = R_k[(p * burn_in):, :]
        self.v_k_samples = v_k[burn_in:, :]
        self.a_k = self.a_k_samples.mean(axis=0)
    def predict(self):
        a = self.a_j[-1,:]
        A = self.A_j[-1,:]
        n = self.n_j[-1,0]
        delta = self.delta
        E_BPS = np.zeros(shape = [mcmc_iter, 1]) # posterior BPS mean
        V_BPS = np.zeros(shape = [mcmc_iter, 1]) # posterior BPS variance
        error = np.zeros(shape = [mcmc_iter, 1])
        mlike = np.zeros(shape = [mcmc_iter, 1])
        for i in range(self.mcmc_iter):
        # sample x(t + 1)
            lambda_ = np.sqrt(0.5 * delta[1] * n/np.random.gamma(shape = delta[1] * n/2)) 
            x_t = np.append(np.array([1]), a + lambda_ * np.matmul(np.random.normal(size = [1, self.p_x]), chol(std_var(np.diag(A)))))
            E_BPS[i] = np.matmul(x_t, self.a_k_samples[i, :])
            V_BPS[i] = np.matmul(x_t, np.matmul(self.R_k_samples[(p*i):(p*(i + 1)), :], x_t.reshape([x_t.shape[0], 1]))) + self.v_k_samples[i, :]
            error[i] = self.y[-1] - E_BPS[i]
            #mlike[i, t] = np.exp(np.log(ss.gamma(0.5 * (nu[t] + 1))) - np.log(ss.gamma(0.5 * nu[t])) - 0.5 * np.log(np.pi * nu[t] * V_BPS[i, t]) - (0.5 * (nu[t] + 1)) * np.log(1 + 1/(nu[t] * V_BPS[i, t]) * (yI[t + 1] - E_BPS[i, t]))**2)
        self.prediction = E_BPS.mean()
        self.variance = V_BPS.mean()
        self.error = error.mean()
        result = [self.prediction, self.variance, self.error]
        return(result)
        
        
      
