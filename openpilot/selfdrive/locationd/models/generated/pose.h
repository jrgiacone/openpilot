#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3654460514432875415);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5462197318257341854);
void pose_H_mod_fun(double *state, double *out_3413546436148806037);
void pose_f_fun(double *state, double dt, double *out_8715702946180776093);
void pose_F_fun(double *state, double dt, double *out_6806979793105738329);
void pose_h_4(double *state, double *unused, double *out_5766790488282858427);
void pose_H_4(double *state, double *unused, double *out_6784399393215802223);
void pose_h_10(double *state, double *unused, double *out_5252621184145006782);
void pose_H_10(double *state, double *unused, double *out_6050564803174162078);
void pose_h_13(double *state, double *unused, double *out_6589030393907913922);
void pose_H_13(double *state, double *unused, double *out_3572125567883469422);
void pose_h_14(double *state, double *unused, double *out_3710584459584419169);
void pose_H_14(double *state, double *unused, double *out_2821158536876317694);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}