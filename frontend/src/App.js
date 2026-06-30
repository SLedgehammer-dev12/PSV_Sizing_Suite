import React, { useState } from 'react';
import { Layout, Menu, Typography, Tabs } from 'antd';
import {
  ExperimentOutlined, FireOutlined, HeatMapOutlined,
  SettingOutlined, ThunderboltOutlined, ApiOutlined,
} from '@ant-design/icons';
import LiquidReliefForm from './components/LiquidReliefForm';
import GasReliefForm from './components/GasReliefForm';
import TwoPhaseForm from './components/TwoPhaseForm';
import FireWettedForm from './components/FireWettedForm';
import './App.css';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

function App() {
  const [collapsed, setCollapsed] = useState(false);

  const items = [
    { key: 'liquid', icon: <ExperimentOutlined />, label: 'Liquid Relief' },
    { key: 'gas', icon: <HeatMapOutlined />, label: 'Gas/Vapor Relief' },
    { key: 'twophase', icon: <ThunderboltOutlined />, label: 'Two-Phase' },
    { key: 'fire', icon: <FireOutlined />, label: 'Fire Scenarios' },
    { key: 'thermal', icon: <SettingOutlined />, label: 'Thermal Expansion' },
    { key: 'api', icon: <ApiOutlined />, label: 'API Reference' },
  ];

  const renderContent = (key) => {
    switch (key) {
      case 'liquid': return <LiquidReliefForm />;
      case 'gas': return <GasReliefForm />;
      case 'twophase': return <TwoPhaseForm />;
      case 'fire': return <FireWettedForm />;
      default: return <LiquidReliefForm />;
    }
  };

  const [selectedKey, setSelectedKey] = useState('liquid');

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Title level={4} style={{ color: '#fff', margin: 0 }}>
            {collapsed ? 'PSV' : 'PSV Sizing'}
          </Title>
        </div>
        <Menu
          theme="dark"
          selectedKeys={[selectedKey]}
          onSelect={({ key }) => setSelectedKey(key)}
          items={items}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Title level={3} style={{ margin: '12px 0' }}>
            PSV Sizing Suite v2.3.0
          </Title>
        </Header>
        <Content style={{ margin: 24 }}>
          {renderContent(selectedKey)}
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
