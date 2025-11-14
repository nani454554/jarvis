import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

const AnimatedOrb = ({ isListening, isConnected }) => {
  const meshRef = useRef();
  const outerRingRef = useRef();
  const middleRingRef = useRef();
  const innerRingRef = useRef();

  useFrame((state) => {
    const time = state.clock.getElapsedTime();

    if (meshRef.current) {
      // Core orb rotation
      meshRef.current.rotation.x = time * 0.2;
      meshRef.current.rotation.y = time * 0.3;

      // Pulsing effect
      const scale = isListening 
        ? 1 + Math.sin(time * 5) * 0.1 
        : 1 + Math.sin(time * 2) * 0.05;
      meshRef.current.scale.set(scale, scale, scale);
    }

    // Rotating rings
    if (outerRingRef.current) {
      outerRingRef.current.rotation.z = time * 0.5;
      outerRingRef.current.rotation.x = Math.sin(time * 0.3) * 0.2;
    }

    if (middleRingRef.current) {
      middleRingRef.current.rotation.z = -time * 0.7;
      middleRingRef.current.rotation.y = Math.cos(time * 0.4) * 0.2;
    }

    if (innerRingRef.current) {
      innerRingRef.current.rotation.z = time * 0.9;
      innerRingRef.current.rotation.x = Math.sin(time * 0.5) * 0.3;
    }
  });

  const ringGeometry = useMemo(() => new THREE.TorusGeometry(1, 0.02, 16, 100), []);

  return (
    <group>
      {/* Core Sphere */}
      <Sphere ref={meshRef} args={[1, 64, 64]}>
        <MeshDistortMaterial
          color={isConnected ? "#00D9FF" : "#FF4444"}
          attach="material"
          distort={0.3}
          speed={2}
          roughness={0.2}
          metalness={0.8}
          emissive={isConnected ? "#00D9FF" : "#FF4444"}
          emissiveIntensity={isListening ? 0.8 : 0.4}
          transparent
          opacity={0.9}
        />
      </Sphere>

      {/* Inner glow */}
      <Sphere args={[1.05, 32, 32]}>
        <meshBasicMaterial
          color={isConnected ? "#00D9FF" : "#FF4444"}
          transparent
          opacity={0.2}
          side={THREE.BackSide}
        />
      </Sphere>

      {/* Rotating Rings */}
      <mesh ref={innerRingRef} geometry={ringGeometry} scale={[1.3, 1.3, 1.3]}>
        <meshStandardMaterial
          color="#00D9FF"
          emissive="#00D9FF"
          emissiveIntensity={0.5}
          transparent
          opacity={0.6}
        />
      </mesh>

      <mesh ref={middleRingRef} geometry={ringGeometry} scale={[1.6, 1.6, 1.6]}>
        <meshStandardMaterial
          color="#0080FF"
          emissive="#0080FF"
          emissiveIntensity={0.4}
          transparent
          opacity={0.5}
        />
      </mesh>

      <mesh ref={outerRingRef} geometry={ringGeometry} scale={[1.9, 1.9, 1.9]}>
        <meshStandardMaterial
          color="#00D9FF"
          emissive="#00D9FF"
          emissiveIntensity={0.3}
          transparent
          opacity={0.4}
        />
      </mesh>

      {/* Point lights */}
      <pointLight position={[0, 0, 0]} intensity={1} color="#00D9FF" />
      <pointLight position={[2, 2, 2]} intensity={0.5} color="#0080FF" />
      <pointLight position={[-2, -2, -2]} intensity={0.5} color="#00D9FF" />
    </group>
  );
};

const OrbScene = ({ isListening, isConnected }) => {
  return (
    <div className="w-full h-full">
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={['transparent']} />
        <ambientLight intensity={0.5} />
        <AnimatedOrb isListening={isListening} isConnected={isConnected} />
        <OrbitControls 
          enableZoom={false} 
          enablePan={false}
          autoRotate
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  );
};

export default OrbScene;
