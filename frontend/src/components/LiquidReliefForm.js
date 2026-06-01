import React, { useState } from 'react';
import {
  Card, Form, InputNumber, Button, Row, Col, Statistic,
  Table, Alert, Divider, Space, message,
} from 'antd';
import { calculateLiquidRelief, getValves } from '../api';

function LiquidReliefForm() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [valves, setValves] = useState([]);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const res = await calculateLiquidRelief({
        q_gpm: values.q_gpm,
        p1_psia: values.p1_psia,
        p2_psia: values.p2_psia,
        g: values.g,
        mu_cp: values.mu_cp,
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
    { title: 'Design', dataIndex: 'design_type', key: 'design_type' },
    { title: 'Size (in)', dataIndex: 'inlet_outlet_size_in', key: 'inlet_outlet_size_in' },
    { title: 'Area (mm²)', dataIndex: 'actual_area_mm2', key: 'actual_area_mm2' },
  ];

  return (
    <Row gutter={24}>
      <Col span={10}>
        <Card title="Liquid Relief - Input" variant="outlined">
          <Form form={form} layout="vertical" onFinish={onFinish}
            initialValues={{ q_gpm: 60, p1_psia: 100, p2_psia: 10, g: 1.0, mu_cp: 1.0, num_valves: 1 }}>
            <Form.Item name="q_gpm" label="Flow Rate (US GPM)" rules={[{ required: true }]}>
              <InputNumber min={0.1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="p1_psia" label="Relieving Pressure P1 (psia)" rules={[{ required: true }]}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="p2_psia" label="Back Pressure P2 (psia)" rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="g" label="Specific Gravity (G)" rules={[{ required: true }]}>
              <InputNumber min={0.01} step={0.1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="mu_cp" label="Viscosity (cP)">
              <InputNumber min={0.1} style={{ width: '100%' }} />
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
                  <Statistic title="Required Area" value={result.Required_Area_Final_sqin} suffix="sq.in" precision={4} />
                </Col>
                <Col span={8}>
                  <Statistic title="Selected Orifice" value={`${result.Selected_Orifice_Letter}`}
                    suffix={`(${result.Selected_Orifice_Area_sqin} sq.in)`} valueStyle={{ color: '#cf1322' }} />
                </Col>
                <Col span={8}>
                  <Statistic title="Reynolds / Kv" value={`${result.Reynolds_Number?.toFixed(0)} / ${result.Kv?.toFixed(3)}`} />
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

export default LiquidReliefForm;
