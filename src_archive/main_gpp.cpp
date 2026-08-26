#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <iomanip>
#include <algorithm>
#include "estimator.h"


int get_col_idx(const std::vector<std::string>& headers, const std::string& target){
    // auto = c# var
    auto it = std::find(headers.begin(), headers.end(), target);

    // end() returns the iterator that points to the empty block of memory right after
    // the last vector value.
    if (it != headers.end()){
        // Iterator math - this is NOT int math.
        return std::distance(headers.begin(), it);
    }
    return -1;
}

int main(){
    std::string input_csv = "data/measured_closed_loops/closed_loop_18-08-2026_20-44-45_3_CW_18m.csv";
    std::string stream_out = "data/golden_references/closed_loop_18-08-2026_20-44-45_3_CW_18m_golden_stream.csv";
    std::string steps_out = "data/golden_references/closed_loop_18-08-2026_20-44-45_3_CW_18m_golden_steps.csv";
    
    // input stream to read files
    std::ifstream file(input_csv);
    if (!file){
        std::cerr << "Error: CSV File not found given path." << std::endl;
        return 1;
    }

    // output streams to write to files
    std::ofstream out_stream(stream_out);
    std::ofstream out_steps(steps_out);

    // Write headers onto files
    out_stream << "seq,is_zvw,instant_quiet,qw,qx,qy,qz,pos_x,pos_y,pos_z\n";
    out_steps << "X,Y\n";
    out_steps << "0.000000,0.000000\n";

    out_stream << std::fixed << std::setprecision(6);
    out_steps << std::fixed << std::setprecision(6);

    // Read headers:
    std::string line;
    std::getline(file, line); // read the first line (till \n into line)
    if (!line.empty() && line.back() == '\r') line.pop_back();

    std::stringstream ss_headers(line);
    std::string col_name;
    std::vector<std::string> headers;
    // Read ss_headers into col_name, split by ',' -> then push into headers list (vector)
    while (std::getline(ss_headers, col_name, ',')){
        headers.push_back(col_name);
    }

    int idx_t_us = get_col_idx(headers, "t_us");
    int idx_seq = get_col_idx(headers, "seq");
    int idx_ax = get_col_idx(headers, "ax");
    int idx_ay = get_col_idx(headers, "ay");
    int idx_az = get_col_idx(headers, "az");
    int idx_gx = get_col_idx(headers, "gx");
    int idx_gy = get_col_idx(headers, "gy");
    int idx_gz = get_col_idx(headers, "gz");


    SystemState state{};
    uint32_t t_last = 0;
    bool first_row = true;

    std::cout << "Starting C++ Simulation...:\n";

    while(std::getline(file, line)){
        if (line.empty()) continue;

        std::stringstream ss(line);
        std::string val;
        std::vector<std::string> row;

        while(std::getline(ss, val, ',')){
            row.push_back(val);
        }
        
        uint32_t t_current = std::stoul(row[idx_t_us]); // stoul = String TO Unsigned Long
        int seq = std::stoi(row[idx_seq]); // String TO Int
        float ax = std::stof(row[idx_ax]); // String TO Float
        float ay = std::stof(row[idx_ay]);
        float az = std::stof(row[idx_az]);
        float gx = std::stof(row[idx_gx]);
        float gy = std::stof(row[idx_gy]);
        float gz = std::stof(row[idx_gz]);

        
        float dt = 0.005f;
        if (first_row) {
            t_last = t_current;
            first_row = false;
        } else {
            dt = (t_current - t_last) / 1000000.0f;
            if (dt <= 0.0f) dt = 0.005f;
            t_last = t_current;
        }
        
        bool is_zvw = update_zvw(state.zvw, ax, ay, az, gx, gy, gz);
        update_mahony(state.mahony, ax, ay, az, gx, gy, gz, dt, state.zvw.instant_quiet);
        
        if (state.mahony.is_initialized){
            update_kinematics(state.kinematics, state.mahony.q, ax, ay, az, dt, is_zvw, state.zvw.dwell_counter);
            if (state.zvw.dwell_counter == DWELL) {
                // write X, Y values to out_steps
                out_steps << state.kinematics.position[0] << "," << state.kinematics.position[1] << "\n";
            }
        }

        
        out_stream << seq << ","
                   << (int)is_zvw << ","
                   << (int)state.zvw.instant_quiet << ","
                   << state.mahony.q[0] << "," << state.mahony.q[1] << "," 
                   << state.mahony.q[2] << "," << state.mahony.q[3] << ","
                   << state.kinematics.position[0] << "," 
                   << state.kinematics.position[1] << "," 
                   << state.kinematics.position[2] << "\n";
    }

    std::cout << "Simulation Complete\n";
    std::cout << "Final XYZ: [" << state.kinematics.position[0] << ", " 
              << state.kinematics.position[1] << ", " << state.kinematics.position[2] << "]\n";

    return 0;
}