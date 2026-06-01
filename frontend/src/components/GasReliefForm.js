import React, { useState } from 'react';
import {
  Card, Form, InputNumber, Select, Button, Row, Col, Statistic,
  Table, Alert, Divider, message, Tag,
} from 'antd';
import { calculateGasRelief, getValves } from '../api';

function GasReliefForm() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [valves, setValves] = useState([]);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const res = await calculateGasRelief({
        w_lb_h: values.w_lb_h,
        p1_psia: values.p1_psia,
        p2_psia: values.p2_psia,
        t_rankine: values.t_rankine,
        z: values.z,
        mw: values.mw,
        k: values.k,
        valve_type: values.valve_type || 'conventional',
        set_pressure_psig: values.set_pressure_psig || values.p1_psia - 14.7,
        num_valves: values.num_valves || 1,
      });
      setResult(res);
      const v = await getValves(res.Selected_Orifice_Letter);
      setValves(v.valves || []);
      message.success('Calculation completed');
    } catch (err) {
      message.error(err.response?.data?.detail || 'Calculation failed');
    } finally {
      setLoading(false);
    }
  };

  const valveColumns = [
    { title: 'Manufacturer', dataIndex: 'manufacturer', key: 'manufacturer' },
    { title: 'Series', dataIndex: 'series', key: 'series' },
    { title: 'Model', dataIndex: 'model_code', key: 'model_code' },
    { title: 'Area (mm²)', dataIndex: 'actual_area_mm2', key: 'actual_area_mm2' },
  ];

  return (
    <Row gutter={24}>
      <Col span={10}>
        <Card title="Gas/Vapor Relief - Input" variant="outlined">
          <Form form={form} layout="vertical" onFinish={onFinish}
            initialValues={{
              w_lb_h: 10000, p1_psia: 500, p2_psia: 14.7,
              t_rankine: 600, z: 0.9, mw: 28, k: 1.4, num_valves: 1,
              valve_type: 'conventional',
            }}>
            <Form.Item name="w_lb_h" label="Mass Flow Rate (lb/h)" rules={[{ required: true }]}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item name="p1_psia" label="P1 (psia)" rules={[{ required: true }]}>
                  <InputNumber min={1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="p2_psia" label="P2 (psia)" rules={[{ required: true }]}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="t_rankine" label="Temperature (°R)" rules={[{ required: true }]}>
              <InputNumber min={100} style={{ width: '100%' }} />
            </Form.Item>
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item name="z" label="Z" rules={[{ required: true }]}>
                  <InputNumber min={0.1} max={3} step={0.05} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="mw" label="MW" rules={[{ required: true }]}>
                  <InputNumber min={1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="k" label="k (Cp/Cv)" rules={[{ required: true }]}>
                  <InputNumber min={1.0} max={2.0} step={0.05} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="valve_type" label="Valve Type">
              <Select>
                <Select.Option value="conventional">Conventional</Select.Option>
                <Select.Option value="balanced_bellows">Balanced Bellows</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item name="num_valves" label="Parallel Valves">
              <InputNumber min={1} max={10} style={{ width: '100%' }} />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">
              CALCULATE
            </Button>
          </Form>
        </Card>
      </Col>
      <Col span={14}>
        {result && (
          <>
            <Card title="Results" variant="outlined">
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="Required Area" value={result.Required_Area_sqin} suffix="sq.in" precision={4} />
                </Col>
                <Col span={8}>
                  <Statistic title="Selected Orifice" value={result.Selected_Orifice_Letter}
                    suffix={`(${result.Selected_Orifice_Area_sqin} sq.in)`} valueStyle={{ color: '#cf1322' }} />
                </Col>
                <Col span={8}>
                  <Statistic title="Flow Regime"
                    value={result.Flow_Type}
                    valueStyle={{ color: result.Flow_Type === 'CRITICAL' ? '#389e0d' : '#fa8c16' }} />
                </Col>
              </Row>
            </Card>
            <Divider />
            <Card title={`Vendor Valves (${valves.length} found)`} variant="outlined">
              <Table dataSource={valves} columns={valveColumns} rowKey="model_code"
                size="small" pagination={{ pageSize: 5 }} />
            </Card>
          </>
        )}
        {!result && (
          <Card>
            <Alert message="Enter inputs and click CALCULATE" type="info" showIcon />
          </Card>
        )}
      </Col>
    </Row>
  );
}

export default GasReliefForm;
